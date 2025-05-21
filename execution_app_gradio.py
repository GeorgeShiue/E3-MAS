import gradio as gr
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import chat_agent_executor
import asyncio
from graph import ExecutionGraph
from langgraph.errors import GraphRecursionError
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

# execution_graph = None

async def stream_chat(user_message, messages, execution_graph):
    print(type(user_message))
    print(user_message)
    yield "", messages, execution_graph # 清空輸入框

    # global execution_graph

    # *第一次輸入判斷模組
    if user_message == "Search" or user_message == "Pipeline":
        executor = user_message + " Executor"
        execution_graph = ExecutionGraph(executor)

        messages.append((user_message, f"已啟用{user_message}模組，請輸入問題..."))
        
        yield "", messages, execution_graph
        return

    config = {"recursion_limit": 30}
    inputs = {
        "input": user_message,
    }
    # write_chat_log(chat_log_path, f"User Query:\n   {inputs['input']}\n\n")

    messages.append((user_message, ""))

    if isinstance(execution_graph, ExecutionGraph):
        inputs["history"] = [] # TODO 也許可以在此幫 Execution Team 加入歷史紀錄(?

    # *若是 Execution Team 的 Pipeline Executor，則等待瀏覽器初始化
    # if isinstance(graph_class, ExecutionGraph) and graph_class.agent.executor_name == "Pipeline Executor":
    #     graph_class.wait_browser_init()

    # start_time = time.time() # 計算執行時間
    execution_result = ""
    response = ""

    try:
        async for event in execution_graph.graph.astream(inputs, config=config):
            for agent, state in event.items():
                if agent == "Solver": # *輸出最終回覆給使用者檢視
                    print("Execution Team Result: " + state["response"] + "\n")
                    execution_result = state["response"]
                    messages.append(("", f"{agent}:\n{execution_result}\n"))
                elif agent != "__end__": # 記錄聊天紀錄
                    # write_chat_log(chat_log_path, f"{agent}:\n")
                    response += f"{agent}:\n"
                    
                    for key, value in state.items():
                        if key == "scores":
                            # progress_rate = compute_progress_rate(value)
                            # write_scores_progress_rate(meta_data_path, value, progress_rate)
                            # write_chat_log(chat_log_path, f"\nProgress Rate: {progress_rate:.2f}\n")
                            pass
                        elif key != "history":
                            # write_chat_log(chat_log_path, f"    {key}: {value}\n")
                            response += f"    {key}: {value}\n"

                    # write_chat_log(chat_log_path, "\n")
                    response += "\n"

                messages[-1] = (user_message, response)  # 更新最新的回覆
                yield "", messages, execution_graph
    except GraphRecursionError as e:
        print(f"GraphRecursionError: {e}")
        # write_chat_log(chat_log_path, f"Reach maximum recursion limit. Task failed.\n")
        messages.append("", f"Reach maximum recursion limit. Task failed.\n")
        yield "", messages, execution_graph

with gr.Blocks() as demo:
    chatbot = gr.Chatbot(
        label="C-pilot",
    )
    user_query = gr.Textbox(placeholder="請輸入 Search 或 Pipeline 以啟用系統模組", label="User")
    execution_graph = gr.State()

    user_query.submit(
        stream_chat,
        inputs=[user_query, chatbot, execution_graph],
        outputs=[user_query, chatbot, execution_graph],
    )

demo.launch(share=True)

# Who is the headmaster of National Central University in Taiwan?