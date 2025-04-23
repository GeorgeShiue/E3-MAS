import asyncio
import os
import shutil
import time
from dotenv import load_dotenv
from typing_extensions import Union, List

from langgraph.errors import GraphRecursionError

from tool import set_agent_parameter_yaml_path
from graph import ExecutionGraph, EvaluationGraph, EvolutionGraph

load_dotenv()
api_key = os.getenv("API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

def clear_chat_log(chat_log_path):
    if os.path.exists(chat_log_path):
        with open(chat_log_path, "w", encoding='utf-8') as f:
            f.write("")
    else:
        print(f"{chat_log_path} does not exist. Skip clearing chat log.")

def write_chat_log(chat_log_path, content):
    with open(chat_log_path, "a", encoding='utf-8') as f:
        f.write(content)

def compute_progress_rate(x: List[float]) -> float:
    if not x:
        return 0.0

    K = len(x)
    max_progress = 0.0

    x_list = []
    for i in range(len(x)):
        temp_list = []
        for j in range(len(x)):
            if j <= i:
                temp_list.append(x[j])
            else:
                temp_list.append(0)
        x_list.append(temp_list)

    for i in range(len(x_list)):
        progress_i = sum(x_list[i]) / K
        max_progress = max(max_progress, progress_i)

    print("Scores: ", x)
    print("Progress Rate: ", max_progress)
    
    return max_progress

async def run_graph_with_graph_class(graph_class: Union[ExecutionGraph, EvaluationGraph], user_input, chat_log_path):
    config = {"recursion_limit": 30}
    inputs = {
        "input": user_input,
        "history": [],
    }

    # clear_chat_log(chat_log_path)
    write_chat_log(chat_log_path, f"User Query:\n   {inputs['input']}\n\n")

    # *若是 Execution Team 的 Web Executor，則等待瀏覽器初始化
    if isinstance(graph_class, ExecutionGraph) and graph_class.agent.executor_name == "Web Executor":
        graph_class.agent.wait_browser_init()

    try:
        async for event in graph_class.graph.astream(inputs, config=config):
            for agent, state in event.items():
                if agent == "Solver": # 輸出最終回覆給使用者檢視
                    print("Execution Team Result: " + state["response"] + "\n")
                elif agent != "__end__": # 記錄聊天紀錄
                    write_chat_log(chat_log_path, f"{agent}:\n")
                    
                    for key, value in state.items():
                        if key == "scores":
                            progress_rate = compute_progress_rate(value)
                            # write_chat_log(chat_log_path, f"\nProgress Rate: {progress_rate:.2f}\n")
                        elif key != "history":
                            write_chat_log(chat_log_path, f"    {key}: {value}\n")

                    write_chat_log(chat_log_path, "\n")
    except GraphRecursionError as e:
        print(f"GraphRecursionError: {e}")
        write_chat_log(chat_log_path, f"Reach maximum recursion limit. Task failed.\n")

def run_app(user_input, executor_name, task, epoch):
    # input(f"Press Enter to start initializing environment and Execution Team for {task} in epoch {epoch}...")
    # print(f"Initializing environment and Execution Team for {task} in epoch {epoch}\n")

    execution_graph = ExecutionGraph(executor_name) # *每次迭代皆須初始化 Execution Team

    # *設定資料夾路徑
    task_folder_path = os.path.join("App Outputs", task)
    epoch_folder_path = os.path.join(task_folder_path, f"epoch_{epoch}")

    agent_parameter_yaml_path = os.path.join(epoch_folder_path, "agent_parameter.yaml")
    execution_chat_log_path = os.path.join(epoch_folder_path, "execution_chat_log.txt")
    evaluation_chat_log_path = os.path.join(epoch_folder_path, "evaluation_chat_log.txt")
    evolution_chat_log_path = os.path.join(epoch_folder_path, "evolution_chat_log.txt")

    evaluation_graph.set_execution_chat_log_path(execution_chat_log_path)
    evolution_graph.set_execution_and_evaluation_chat_log_path(execution_chat_log_path, evaluation_chat_log_path)

    # *建立與清理資料夾路徑
    if os.path.exists(epoch_folder_path):
        shutil.rmtree(epoch_folder_path)
        print(f"Reset {epoch_folder_path}.")
    os.makedirs(epoch_folder_path, exist_ok=True)
    print(f"Set folder path to: {epoch_folder_path}")    

    print(f"Environment and Execution Team for {task} in epoch {epoch} are initialized\n")

    # *將上個版本的 agent_parameter.yaml 複製到 epoch 資料夾內
    # TODO 之後要改成複製上一個epoch的agent_parameter.yaml
    if epoch == 1:
        shutil.copy("agent_parameter_base.yaml", agent_parameter_yaml_path)
    else:
        shutil.copy(os.path.join(task_folder_path, f"epoch_{epoch-1}", "agent_parameter.yaml"), agent_parameter_yaml_path)
    set_agent_parameter_yaml_path(agent_parameter_yaml_path)

    # *若是 Execution Team 的 Web Executor，則設定截圖資料夾路徑
    if executor_name == "Web Executor":
        screenshot_folder_path = os.path.join(epoch_folder_path, "screenshot")
        execution_graph.set_screenshot_folder_path(screenshot_folder_path)

    # *啟動 Dynamic MAS
    input(f"Press Enter to start running Dynamic MAS for {task} in epoch {epoch}...")
    print(f"Dynamic MAS for {task} in epoch {epoch} start running.\n")
    start_time = time.time()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(run_graph_with_graph_class(execution_graph, user_input, execution_chat_log_path)) # *Test Execution Team
    loop.run_until_complete(run_graph_with_graph_class(evaluation_graph, "Please evaluate the performance of execution team.", evaluation_chat_log_path)) # *Test Evaluation Team
    loop.run_until_complete(run_graph_with_graph_class(evolution_graph, "Please analyze the evaluation result of the execution team.", evolution_chat_log_path)) # *Test Evolution Team
    loop.close()

    end_time = time.time()
    print(f"\nDynamic MAS run time: {end_time - start_time} seconds")

    # * 測試 Execution Team 的 Web Executor 時，必須在這裡清除selenium controller的container
    # if execution_graph.agent.executor_name == "Web Executor":
    #     execution_graph.agent.tool.selenium_controller.clean_containers() # *selenium controller解構子有問題，必須runtime內清除

# * 初始化 Evaluation Team、Evolution Team
evaluation_graph = EvaluationGraph() 
evolution_graph = EvolutionGraph()

# *設定任務
# Who is the headmaster of National Central University in Taiwan?
# Summarize the content of the 111 Academic Affairs Regulations.
# Please help me gather information related to scholarship applications.
# Please help me perform a series of operation to apply leave application. You can stop at fininsh click '申請' button.
user_input = "Please help me gather information related to scholarship applications." # *給 Execution Team 的使用者輸入
executor_name = "Search Executor" # *"Search Executor" or "Web Executor"
task = "Scholarship Application"
max_epoch = 5

# *測試 Dynamic MAS 多次迭代
for epoch in range(max_epoch):
    run_app(user_input, executor_name, task, epoch + 1)