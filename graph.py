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
        state["history"].append(("Executor", (task, agent_response["messages"][-1].content)))

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
            return "solver"
        else:
            return "executor"
        
    def create_execution_graph(self):
        clean_graph = StateGraph(self.PlanExecute)

        # TODO node定義可以再更抽象化
        clean_graph.add_node("planner", self.plan_step)
        clean_graph.add_node("executor", self.execute_step)
        clean_graph.add_node("replanner", self.replan_step)
        clean_graph.add_node("solver", self.solve_step)

        clean_graph.add_edge(START, "planner")
        clean_graph.add_edge("planner", "executor")
        clean_graph.add_edge("executor", "replanner")
        clean_graph.add_conditional_edges(
            "replanner",
            # Next, we pass in the function that will determine which node is called next.
            self.should_end,
            ["executor", "solver"],
        )
        clean_graph.add_edge("solver", END)

        graph = clean_graph.compile() # This compiles it into a LangChain Runnable, meaning you can use it as you would any other runnable
        GraphFactory.save_graph_mermaid(graph, "Execution Graph") # 測試GraphFactory的save_graph_mermaid功能
        print("Execution Graph is created.\n")

        return graph
    
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
        print("Evaluation Graph is created.\n")
        
        return graph

        
if __name__ == "__main__":
    import asyncio
    import os
    import shutil
    import time
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

    executor_name = "Web Executor" # "Search Executor" or "Web Executor"
    # execution_graph = ExecutionGraph(executor_name) # Init Execution Team
    evaluation_graph = EvaluationGraph() # Init Evaluation Team

    screenshot_folder_path = os.path.join("Outputs", "screenshots")
    execution_chat_log_path = os.path.join("Outputs", "execution_chat_log.txt")
    evaluation_chat_log_path = os.path.join("Outputs", "evaluation_chat_log.txt")

    # if os.path.exists(screenshot_folder_path):
    #     shutil.rmtree(screenshot_folder_path)
    # os.makedirs(screenshot_folder_path, exist_ok=True)

    def clear_chat_log(chat_log_path):
        with open(chat_log_path, "w", encoding='utf-8') as f:
            f.write("")

    def write_to_chat_log(chat_log_path, content):
        with open(chat_log_path, "a", encoding='utf-8') as f:
            f.write(content)

    async def run_graph_with_graph_class(graph_class: Union[ExecutionGraph, EvaluationGraph], user_input, chat_log_path):
        config = {"recursion_limit": 30}
        inputs = {
            "input": user_input,
            "history": [],
        }

        clear_chat_log(chat_log_path)
        write_to_chat_log(chat_log_path, f"User Query:\n{inputs['input']}\n\n")

        # *若是 Execution Team 的 Web Executor，則等待瀏覽器初始化
        if isinstance(graph_class, ExecutionGraph) and graph_class.agent.executor_name == "Web Executor":
            graph_class.agent.wait_browser_init()

        async for event in graph_class.graph.astream(inputs, config=config):
            for agent, state in event.items():
                if agent != "__end__":
                    write_to_chat_log(chat_log_path, f"{agent}:\n")

                    for key, value in state.items():
                        if (key != "history"):
                            write_to_chat_log(chat_log_path, f"{key}: {value}\n")
                    
                    write_to_chat_log(chat_log_path, "\n")

    # Who is the headmaster of National Central University in Taiwan?
    # Summarize the content of the 111 Academic Affairs Regulations.
    # Please help me gather information related to scholarship applications.
    # Please help me perform a series of operation to apply leave application. You can stop at fininsh click '申請' button.
    user_input = "Please help me perform a series of operation to apply leave application. You can stop at fininsh click '申請' button."

    module_name = "Execution Team" # Execution Team or Evaluation Team or Evolution Team
    print(f"{module_name} start running...\n")

    start_time = time.time()
    loop = asyncio.new_event_loop()
    # loop.run_until_complete(run_graph_with_graph_class(execution_graph, user_input, execution_chat_log_path)) # *Test Execution Team
    loop.run_until_complete(run_graph_with_graph_class(evaluation_graph, "Please evaluate the performance of execution team.", evaluation_chat_log_path)) # *Test Evaluation Team
    end_time = time.time()

    print(f"\n{module_name} Run Time: {end_time - start_time} seconds\n")

    # if execution_graph.agent.executor_name == "Web Executor":
    #     execution_graph.agent.execution_tool.selenium_controller.clean_containers() # *selenium controller解構子有問題，必須runtime內清除