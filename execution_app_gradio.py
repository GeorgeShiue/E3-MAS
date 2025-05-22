import os
import shutil
import gradio as gr

from typing import List
from dotenv import load_dotenv
from langgraph.errors import GraphRecursionError
from base64 import b64encode

from graph import ExecutionGraph

load_dotenv()
api_key = os.getenv("API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

SCREENSHOT_FOLDER_PATH = "App Outputs/Screenshot"

def clean_containers(graph: ExecutionGraph):
    if isinstance(graph, ExecutionGraph) and graph.agent.executor_name == "Pipeline Executor":
        graph.agent.tool.selenium_controller.clean_containers()

async def stream_chat(user_message, messages: List[gr.ChatMessage], execution_graph: ExecutionGraph):
    yield "", messages, execution_graph # 清空輸入框

    # * 設定等待時訊息顯示
    messages.append(gr.ChatMessage(role="user", content=user_message))
    yield "", messages, execution_graph

    # *第一次輸入選擇模組
    if user_message == "Search" or user_message == "Pipeline":
        executor = user_message + " Executor"
        execution_graph = ExecutionGraph(executor)

        messages.append(gr.ChatMessage(role="assistant", content=f"已啟用{user_message}模組，請輸入問題..."))
        yield "", messages, execution_graph

        return

    messages.append(gr.ChatMessage(role="assistant", content="啟動模組對話中，請稍後..."))
    yield "", messages, execution_graph

    config = {"recursion_limit": 30}
    inputs = {
        "input": user_message,
        "history": [], # TODO 可以在此幫 Execution Team 加入歷史紀錄
    }

    # *若是 Pipeline 模組，則等待瀏覽器初始化，並重新設定截圖資料夾
    if execution_graph.agent.executor_name == "Pipeline Executor":
        execution_graph.wait_browser_init()

        if os.path.exists(SCREENSHOT_FOLDER_PATH):
            shutil.rmtree(SCREENSHOT_FOLDER_PATH)
        os.makedirs(SCREENSHOT_FOLDER_PATH, exist_ok=True)
        execution_graph.set_screenshot_folder_path(SCREENSHOT_FOLDER_PATH)

    try:
        async for event in execution_graph.graph.astream(inputs, config=config):
            for agent, state in event.items():
                # *輸出最終回覆給使用者檢視
                if agent == "Solver": 
                    messages.append(gr.ChatMessage(role="assistant", content=f"Final Response:\n{state['response']}\n"))
                # *記錄聊天紀錄
                elif agent != "__end__": 
                    response = f"{agent}:\n" 
                    for key, value in state.items():
                        if key != "history":
                            response += f"    {key}: {value}\n"

                    # *顯示 Pipeline 模組操作結果截圖
                    if agent == "Pipeline Executor":
                        current_screenshot_name = execution_graph.get_current_screenshot_name()
                        current_screenshot_path = os.path.join(SCREENSHOT_FOLDER_PATH, current_screenshot_name + ".png")
                        with open(current_screenshot_path, "rb") as f:
                            data = b64encode(f.read()).decode("utf-8")
                            response += f"![{current_screenshot_name}](data:image/png;base64,{data})\n"

                    messages.append(gr.ChatMessage(role="assistant", content=response))

                yield "", messages, execution_graph
        clean_containers(execution_graph)
    except GraphRecursionError as e:
        print(f"GraphRecursionError: {e}")
        messages.append(gr.ChatMessage(role="assistant", content="Reach maximum recursion limit. Task failed.\n"))

        yield "", messages, execution_graph
        clean_containers(execution_graph)

with gr.Blocks(css=".fullscreen-chatbot { height: calc(100vh - 200px) !important; overflow-y: auto; ") as demo:
    init_message = [
        gr.ChatMessage(role="assistant", content="請輸入 Search 或 Pipeline 以啟用系統模組"),
    ]
    chatbot = gr.Chatbot(value=init_message, type="messages", label="C-pilot", elem_classes="fullscreen-chatbot")
    user_query = gr.Textbox(placeholder="選用模組後請輸入需求，ex: Who is the headmaster of National Central University in Taiwan?", label="User")
    execution_graph = gr.State()

    user_query.submit(
        stream_chat,
        inputs=[user_query, chatbot, execution_graph],
        outputs=[user_query, chatbot, execution_graph],
    )

demo.launch()

# Who is the headmaster of National Central University in Taiwan?

# Please help me apply leave application.
# Start Date is 2025/4/29 and End Date is 2025/4/30.
# I want to apply 事假 because I have to 回家.
# My leave certificate is in the path C:\\Users\\George\\Desktop\\專題Program\\專題\\Docs\\leave_reason.png.