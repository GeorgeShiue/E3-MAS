import operator
from typing import Annotated, List, Tuple, Any
from typing_extensions import TypedDict
from io import BytesIO
from PIL import Image
from langgraph.graph import StateGraph, START, END

from agent import Response, planner, executor, replanner, solver


# Define Graph State
class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    history: List[Tuple[str, Any]]



# Define Agent Node Function
# * 不同 Agent Node Function 各自定義以實現訊息流區隔
async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({"user_input": [("user", state["input"])]}) # 對應到planner system prompt中的{user_input}
    state["history"].append(("Planner", plan.steps)) # 將plan的步驟加入history中

    return {
        "plan": plan.steps,
        "history": state["history"],
    }

async def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"""For the following plan:
{plan_str}\n\nYou are tasked with executing step {1}, {task}."""
    agent_response = await executor.ainvoke({"messages": [("user", task_formatted)]}) # react agent 用 messages 方式接收訊息
    state["history"].append(("Executor", (task, agent_response["messages"][-1].content)))

    return {
        "past_steps": [(task, agent_response["messages"][-1].content)], # react agent 接收訊息方式
        "history": state["history"],
    }

async def replan_step(state: PlanExecute):
    # 過濾掉state中不需要的欄位
    temp_state = state.copy()
    temp_state.pop("history")

    output = await replanner.ainvoke(temp_state)
    if isinstance(output.action, Response):
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

async def solve_step(state: PlanExecute):
    print("history:")
    print(state["history"])
    response = await solver.ainvoke({"user_input": state["input"], "planning_history": state["history"]})
    return {"response": response.content, "history": state["history"]}



# Define Conditional Edge Function
def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return "solver"
    else:
        return "executor"
    


# Create Graph
workflow = StateGraph(PlanExecute)

workflow.add_node("planner", plan_step)
workflow.add_node("executor", execute_step)
workflow.add_node("replanner", replan_step)
workflow.add_node("solver", solve_step)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "replanner")
workflow.add_conditional_edges(
    "replanner",
    # Next, we pass in the function that will determine which node is called next.
    should_end,
    ["executor", "solver"],
)
workflow.add_edge("solver", END)

app = workflow.compile() # This compiles it into a LangChain Runnable, meaning you can use it as you would any other runnable



# Save the graph image
graph_bytes = app.get_graph(xray=True).draw_mermaid_png()

output_file_path = "graph.png"
with BytesIO(graph_bytes) as byte_stream:
    image = Image.open(byte_stream)
    image.save(output_file_path, format="PNG")

print(f"Graph image saved to: {output_file_path}")