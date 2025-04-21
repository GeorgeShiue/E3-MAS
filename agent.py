from typing import List, Union

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from tool import ExecutionTool, WebOperationTool

from utils.agent_factory import AgentFactory

import threading

# Execution Team Agent
class ExecutionAgent():
    # Execution Team Response
    class Plan(BaseModel):
        """Plan to follow in future"""

        steps: List[str] = Field(
            description="different steps to follow, should be in sorted order"
        )

    class Response(BaseModel):
        """Response to user."""

        response: str

    class Act(BaseModel):
        """Action to perform."""

        action: Union['ExecutionAgent.Response', 'ExecutionAgent.Plan'] = Field(
            description="Action to perform. If you want to respond to user, use Response. "
            "If you need to further use tools to get the answer, use Plan."
        )

    def __init__(self):
        self.execution_tool = ExecutionTool()
        self.web_operation_tool = WebOperationTool()

        # 啟動瀏覽器初始化執行緒
        self.create_browser_thread = threading.Thread(
            target=self.web_operation_tool.create_browser,
            daemon=True  # 確保主程式結束時，執行緒也會結束
        )
        self.create_browser_thread.start()

        self.planner = self.create_planner_agent()
        self.executor = self.create_executor_agent()
        self.web_executor = self.create_web_executor_agent()
        self.replanner = self.create_replanner_agent()
        self.solver = self.create_solver_agent()

    def create_planner_agent(self):
        # * Plannger Agent 使用 ChatPromptTemplate.from_messages() 搭配 with_structured_output(Plan) 實現
        llm_config, planner_system_prompt, tool_list = AgentFactory.extract_agent_parameter_yaml("Planner")

        planner_llm = ChatOpenAI(model=llm_config["model"], temperature=llm_config["temperature"])
        planner_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", planner_system_prompt),
                ("placeholder", "{user_input}"), # placeholer 用來動態嵌入使用者輸入的訊息
            ]
        )

        AgentFactory.print_agent_parameter("Planner")

        planner = planner_prompt | planner_llm.with_structured_output(self.Plan) # 限制使用特定模板回答問題
        return planner

    def create_executor_agent(self):
        executor = AgentFactory.create_react_agent_with_yaml("Executor", self.execution_tool.tool_dict)
        return executor
    
    def create_web_executor_agent(self):
        web_executor = AgentFactory.create_react_agent_with_yaml("Web Executor", self.web_operation_tool.tool_dict)
        return web_executor

    def create_replanner_agent(self):
        # * Replanner Agent 使用 ChatPromptTemplate.from_template() 搭配 with_structured_output(Act) 實現
        llm_config, replanner_system_prompt, tool_list = AgentFactory.extract_agent_parameter_yaml("Replanner")

        replanner_llm = ChatOpenAI(model=llm_config["model"], temperature=llm_config["temperature"]) # ! Replanner需要使用gpt-4o才不會一直call tools
        replanner_prompt = ChatPromptTemplate.from_template(replanner_system_prompt)
        
        AgentFactory.print_agent_parameter("Replanner")

        replanner = replanner_prompt | replanner_llm.with_structured_output(self.Act) # 限制使用特定模板回答問題
        return replanner

    def create_solver_agent(self):
        # * Solver Agent 使用 ChatPromptTemplate.from_template() 實現        
        llm_config, solver_system_prompt, tool_list = AgentFactory.extract_agent_parameter_yaml("Solver")

        solver_llm = ChatOpenAI(model=llm_config["model"])
        solver_prompt = ChatPromptTemplate.from_template(solver_system_prompt)

        AgentFactory.print_agent_parameter("Solver")

        solver = solver_prompt | solver_llm
        return solver

# Evaluation Team Agent
class EvaluationAgent():
    def __init__(self):
        self.critic = AgentFactory.create_react_agent_with_yaml("Critic")
        self.evaluator = AgentFactory.create_react_agent_with_yaml("Evaluator")

# Evolution Team Agent
class EvolutionAgent():
    def __init__(self):
        self.analyzer = AgentFactory.create_react_agent_with_yaml("Analyzer")
        self.prompt_optimizer = AgentFactory.create_react_agent_with_yaml("Prompt Optimizer")



if __name__ == "__main__":
    import time
    import os
    from dotenv import load_dotenv

    from utils.selenium_controller import SeleniumController

    start_time = time.time()

    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

    execution_agent = ExecutionAgent()

    # # 啟動瀏覽器初始化執行緒
    # create_browser_thread = threading.Thread(
    #     target=execution_agent.web_operation_tool.create_browser,
    #     daemon=True  # 確保主程式結束時，執行緒也會結束
    # )
    # create_browser_thread.start()

    planner = execution_agent.planner
    # executor = execution_agents.executor
    executor = execution_agent.web_executor # 測試 web executor
    replanner = execution_agent.replanner
    solver = execution_agent.solver

    # execution_agent.web_operation_tool.create_browser() # TODO async create browser

    if execution_agent.create_browser_thread.is_alive():
        print("browser is starting...")
        execution_agent.create_browser_thread.join()
    print("browser is ready")

    response = planner.invoke({"user_input": [("user", "Please help me apply leave application.")]})
    for step in response.steps:
        print(step)
    
    responses = []

    # Step 1. function_name: 'navigate_with_url', parameters: '{\"url\":\"https://cis.ncu.edu.tw/iNCU/stdAffair/leaveRequest\"}'
    responses.append(executor.invoke({"messages": [("user", "Step 1. Navigate to https://cis.ncu.edu.tw/iNCU/stdAffair/leaveRequest")]}))
    responses.append(executor.invoke({"messages": [("user", "Step 2. function_name: 'input_text_with_label', parameters: '{\"label_text\":\"Account\",\"text\":\"user_account\",\"privacy\":\"Account\"}'")]}))
    responses.append(executor.invoke({"messages": [("user", "Step 3. function_name: 'input_text_with_label', parameters: '{\"label_text\":\"Password\",\"text\":\"user_password\",\"privacy\":\"Password\"}'")]}))
    responses.append(executor.invoke({"messages": [("user", "Step 4. function_name: 'click_button_with_text', parameters: '{\"text\":\"Login to Portal\"}'")]}))
    responses.append(executor.invoke({"messages": [("user", "Step 5. function_name: 'click_button_with_text', parameters: '{\"text\":\"Go to\"}'")]}))
    responses.append(executor.invoke({"messages": [("user", "Step 6. function_name: 'click_button_with_text', parameters: '{\"text\":\"申請\"}'")]}))

    for response in responses:
        print("Response: " + response["messages"][-1].content)

    end_time = time.time()

    print(f"Execution time: {end_time - start_time} seconds")

    execution_agent.web_operation_tool.selenium_controller.clean_containers() # *selenium controller解構子有問題，必須runtime內清除