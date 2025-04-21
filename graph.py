import operator
from io import BytesIO
from typing import Annotated, Any, List, Tuple

from PIL import Image
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from agent import ExecutionAgent



class ExecutionGraph():
    # Define Graph State
    class PlanExecute(TypedDict):
        input: str
        plan: List[str]
        past_steps: Annotated[List[Tuple], operator.add]
        response: str
        history: List[Tuple[str, Any]]

    def __init__(self):
        self.agent = ExecutionAgent()
        self.app = self.create_graph()
        self.name = "ExecutionGraph"

    def save_graph_mermaid(self):

        graph_bytes = self.app.get_graph(xray=True).draw_mermaid_png()
        
        # save to Outputs folder
        output_file_path = os.path.join("Outputs", self.name) + ".png"
        with BytesIO(graph_bytes) as byte_stream:
            image = Image.open(byte_stream)
            image.save(output_file_path, format="PNG")

        # display(Image(execution_app.get_graph(xray=True).draw_mermaid_png()))
        
        print(f"Graph mermaid image saved to: {output_file_path}")

    # Define Agent Node Function
    # * 不同 Agent Node Function 各自定義以實現訊息流區隔
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
        


    def create_graph(self):
        # Create Graph
        graph = StateGraph(self.PlanExecute)

        # TODO node定義可以再更抽象化
        graph.add_node("planner", self.plan_step)
        graph.add_node("executor", self.execute_step)
        graph.add_node("replanner", self.replan_step)
        graph.add_node("solver", self.solve_step)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "executor")
        graph.add_edge("executor", "replanner")
        graph.add_conditional_edges(
            "replanner",
            # Next, we pass in the function that will determine which node is called next.
            self.should_end,
            ["executor", "solver"],
        )
        graph.add_edge("solver", END)

        app = graph.compile() # This compiles it into a LangChain Runnable, meaning you can use it as you would any other runnable
        return app
    

if __name__ == "__main__":
    # load api key from .env file
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

    # import time

    # start_time = time.time()

    execution_graph = ExecutionGraph()
    # execution_graph.save_graph_mermaid()

    # end_time = time.time()

    # print(f"ExecutionGraph created in {end_time - start_time} seconds")

    import asyncio
    import nest_asyncio
    import time

    with open("Outputs/execution_chat_log.txt", "w", encoding='utf-8') as f:
        f.write("")

    def write_to_chat_log(content):
        with open("Outputs/execution_chat_log.txt", "a", encoding='utf-8') as f:
            f.write(content)

    # Who is the headmaster of National Central University in Taiwan?
    # Summarize the content of the 111 Academic Affairs Regulations.
    # Please help me gather information related to scholarship applications.
    # Please help me fill out the leave application on the school website.
    config = {"recursion_limit": 30}
    inputs = {
        "input": "Please help me gather information related to scholarship applications.",
        "history": [], # 初始化儲存History的list
    }
    write_to_chat_log(f"User Query:\n{inputs['input']}\n\n")

    # tool_dict["create_browser"].invoke(input=None)

    nest_asyncio.apply()
    loop = asyncio.get_event_loop()

    async def run_graph():
        async for event in execution_graph.app.astream(inputs, config=config):
            for agent, state in event.items():
                if agent != "__end__":
                    write_to_chat_log(f"{agent}:\n")

                    for key, value in state.items():
                        if (key != "history"):
                            write_to_chat_log(f"{key}: {value}\n")
                    
                    write_to_chat_log("\n")
        

    start_time = time.time()
    loop.run_until_complete(run_graph())
    end_time = time.time()

    print(f"Execution Team Run Time: {end_time - start_time} seconds")
    # del tools.selenium_controller