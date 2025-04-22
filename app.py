import os
from dotenv import load_dotenv
import asyncio
import time
import shutil
from graph import ExecutionGraph 



load_dotenv()
api_key = os.getenv("API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

executor_name = "Web Executor" # "Search Executor" or "Web Executor"
execution_graph = ExecutionGraph(executor_name) # *先定義便可先創建browser

def clear_chat_log(chat_log_path):
    with open(chat_log_path, "w", encoding='utf-8') as f:
        f.write("")

def write_to_chat_log(chat_log_path,content):
    with open(chat_log_path, "a", encoding='utf-8') as f:
        f.write(content)

async def run_graph_with_graph_class(graph_class, user_input, chat_log_path):
    config = {"recursion_limit": 30}
    inputs = {
        "input": user_input,
        "history": [], # 初始化儲存History的list
    }

    clear_chat_log(chat_log_path)
    write_to_chat_log(chat_log_path, f"User Query:\n{inputs['input']}\n\n")

    # *若是Execution Team 的 Web Executor，則等待瀏覽器初始化
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

SCREENSHOTS_FOLDER_PATH = os.path.join("Outputs", "screenshots")
EXECUTION_CHAT_LOG_PATH = os.path.join("Outputs", "execution_chat_log.txt")

if os.path.exists(SCREENSHOTS_FOLDER_PATH):
    shutil.rmtree(SCREENSHOTS_FOLDER_PATH)
os.makedirs(SCREENSHOTS_FOLDER_PATH, exist_ok=True)

# Who is the headmaster of National Central University in Taiwan?
# Summarize the content of the 111 Academic Affairs Regulations.
# Please help me gather information related to scholarship applications.
# Please help me perform a series of operation to apply leave application. You can stop at fininsh click '申請' button.
user_input = "Please help me perform a series of operation to apply leave application. You can stop at fininsh click '申請' button."

print("Execution Team start running...\n")

start_time = time.time()
loop = asyncio.new_event_loop()
loop.run_until_complete(run_graph_with_graph_class(execution_graph, user_input, EXECUTION_CHAT_LOG_PATH))
end_time = time.time()

print(f"\nExecution Team Run Time: {end_time - start_time} seconds\n")

if execution_graph.agent.executor_name == "Web Executor":
    execution_graph.agent.execution_tool.selenium_controller.clean_containers() # *selenium controller解構子有問題，必須runtime內清除