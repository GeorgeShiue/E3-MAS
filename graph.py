import operator
from typing import Annotated, Any, List, Tuple

from typing_extensions import TypedDict, Union
from langgraph.graph import END, START, StateGraph

from agent import ExecutionAgent, EvaluationAgent, EvolutionAgent
from utils.factory import GraphFactory


class ExecutionGraph():
    class PlanExecute(TypedDict):
        input: str
        plan: List[str]
        past_steps: Annotated[List[Tuple], operator.add]
        response: str
        history: List[Tuple[str, Any]]

    def __init__(self, executor_name):
        self.executor_name = executor_name
        self.agent = ExecutionAgent(self.executor_name)
        self.graph = self.create_execution_graph()

    # * Define Agent Node Function, 不同 Agent Node Function 各自定義以實現訊息流區隔
    async def plan_step(self, state: PlanExecute):
        plan = await self.agent.planner.ainvoke({"user_input": [("user", state["input"])]}) # 對應到planner system prompt中的{user_input}
        state["history"].append(("Planner", plan.steps)) # 將plan的步驟加入history中

        return {
            "plan": plan.steps,
            "history": state["history"],
        }

    async def execute_step(self, state: PlanExecute):
        plan = state["plan"]
        plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
        task = plan[0]
        task_formatted = f"""For the following plan:
    {plan_str}\n\nYou are tasked with executing step {1}, {task}."""
        agent_response = await self.agent.executor.ainvoke({"messages": [("user", task_formatted)]}) # react agent 用 messages 方式接收訊息
        state["history"].append((self.executor_name, (task, agent_response["messages"][-1].content)))

        return {
            "past_steps": [(task, agent_response["messages"][-1].content)], # react agent 接收訊息方式
            "history": state["history"],
        }

    async def replan_step(self, state: PlanExecute):
        # 過濾掉state中不需要的欄位
        temp_state = state.copy()
        temp_state.pop("history")

        output = await self.agent.replanner.ainvoke(temp_state)
        if isinstance(output.action, ExecutionAgent.Response):
            state["history"].append(("Replanner", output.action.response))
            return {
                "response": output.action.response,
                "history": state["history"],
            }
        else:
            state["history"].append(("Replanner", output.action.steps))
            return {
                "plan": output.action.steps,
                "history": state["history"],
            }

    async def solve_step(self, state: PlanExecute):
        response = await self.agent.solver.ainvoke({"user_input": state["input"], "planning_history": state["history"]})
        return {"response": response.content, "history": state["history"]}

    # Define Conditional Edge Function
    def should_end(self, state: PlanExecute):
        if "response" in state and state["response"]:
            return "Solver"
        else:
            return self.executor_name
        
    def create_execution_graph(self):
        clean_graph = StateGraph(self.PlanExecute)

        # TODO node定義可以再更抽象化
        clean_graph.add_node("Planner", self.plan_step)
        clean_graph.add_node(self.executor_name, self.execute_step)
        clean_graph.add_node("Replanner", self.replan_step)
        clean_graph.add_node("Solver", self.solve_step)

        clean_graph.add_edge(START, "Planner")
        clean_graph.add_edge("Planner", self.executor_name)
        clean_graph.add_edge(self.executor_name, "Replanner")
        clean_graph.add_conditional_edges(
            "Replanner",
            # Next, we pass in the function that will determine which node is called next.
            self.should_end,
            [self.executor_name, "Solver"],
        )
        clean_graph.add_edge("Solver", END)

        graph = clean_graph.compile() # This compiles it into a LangChain Runnable, meaning you can use it as you would any other runnable
        # GraphFactory.save_graph_mermaid(graph, "Execution Graph") # 測試GraphFactory的save_graph_mermaid功能
        print("Execution Graph is created.")

        return graph
    
    def set_screenshot_folder_path(self, screenshot_folder_path):
        self.agent.tool.selenium_controller.screenshot_folder_path = screenshot_folder_path
        print(f"Set screenshot folder path to: {screenshot_folder_path}")

    def wait_browser_init(self):
        if self.agent.create_browser_thread.is_alive():
            print("browser is starting...")
            self.agent.create_browser_thread.join()
        print("browser is ready")

class EvaluationGraph():
    class Evaluation(TypedDict):
        input: str
        rubric: str
        result: str
        scores: List[float]

    def __init__(self):
        self.agent = EvaluationAgent()
        self.graph = self.create_evaluation_graph()
    
    async def critic_step(self, state: Evaluation):
        response = await self.agent.critic.ainvoke({"messages": [("user", state["input"])]})
        state["rubric"] = response["messages"][-1].content # 儲存評估標準到state內
        return {
            "rubric": state["rubric"],
        }

    async def evaluator_step(self, state: Evaluation):
        response = await self.agent.evaluator.ainvoke({"messages": [("user", state["rubric"])]})
        state["result"] = response["messages"][-1].content # 儲存評估結果到state內
        state["scores"] = response["structured_response"].scores # 儲存評估分數到state內
        return {
            "result": state["result"],
            "scores": state["scores"],
        }

    def create_evaluation_graph(self):
        clean_graph = StateGraph(self.Evaluation)

        clean_graph.add_node("critic", self.critic_step)
        clean_graph.add_node("evaluator", self.evaluator_step)

        clean_graph.add_edge(START, "critic")
        clean_graph.add_edge("critic", "evaluator")
        clean_graph.add_edge("evaluator", END)

        graph = clean_graph.compile() # This compiles it into a LangChain Runnable, meaning you can use it as you would any other runnable
        # GraphFactory.save_graph_mermaid(graph, "Evaluation Graph") # 測試GraphFactory的save_graph_mermaid功能
        print("Evaluation Graph is created.")
        
        return graph
    
    def set_execution_chat_log_path(self, execution_chat_log_path):
        self.agent.tool.execution_chat_log_path = execution_chat_log_path
        print(f"Set execution chat log path to: {execution_chat_log_path} for Evaluation Graph")

class EvolutionGraph():
    class Evolution(TypedDict):
        input: str
        analysis: str
        result: str

    def __init__(self):
        self.agent = EvolutionAgent()
        self.graph = self.create_evolution_graph()

    async def analyze_step(self, state: Evolution):
        response = await self.agent.analyzer.ainvoke({"messages": [("user", state["input"])]})
        return {
            "analysis": response["messages"][-1].content # 儲存分析結果到state內
        }

    async def prompt_optimize_step(self, state: Evolution):
        response = await self.agent.prompt_optimizer.ainvoke({"messages": [("user", state["analysis"])]})
        return {
            "result": response["messages"][-1].content, # 儲存最終回覆到state內,
        }

    def create_evolution_graph(self):
        clean_graph = StateGraph(self.Evolution)

        clean_graph.add_node("analyzer", self.analyze_step)
        clean_graph.add_node("prompt_optimizer", self.prompt_optimize_step)

        clean_graph.add_edge(START, "analyzer")
        clean_graph.add_edge("analyzer", "prompt_optimizer")
        clean_graph.add_edge("prompt_optimizer", END)

        graph = clean_graph.compile()
        # GraphFactory.save_graph_mermaid(graph, "Evolution Graph") # 測試GraphFactory的save_graph_mermaid功能
        print("Evolution Graph is created.")

        return graph
    
    def set_execution_and_evaluation_chat_log_path(self, execution_chat_log_path, evaluation_chat_log_path):
        self.agent.tool.execution_chat_log_path = execution_chat_log_path
        self.agent.tool.evaluation_chat_log_path = evaluation_chat_log_path
        print(f"Set execution chat log path to: {execution_chat_log_path} and evaluation chat log path to: {evaluation_chat_log_path} for Evolution Graph")

    def set_executor_name(self, executor_name):
        self.agent.tool.executor_name = executor_name
        print(f"Set executor name to: {executor_name} for Evolution Graph")

if __name__ == "__main__":
    import asyncio
    import os
    import shutil
    import time
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

    execution_graph = ExecutionGraph("Search Executor")
    # evolution_graph = EvolutionGraph()