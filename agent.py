import threading
from typing import List, Union

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from tool import SearchExecutionTool, WebExecutionTool, EvaluationTool, EvolutionTool
from utils.factory import AgentFactory

class ExecutionAgent():
    # Response Class
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

    def __init__(self, executor_name):
        self.executor_name = executor_name

        self.tool = self.init_execution_tool()

        self.planner = self.create_planner_agent()
        self.executor = self.create_executor_agent()
        self.replanner = self.create_replanner_agent()
        self.solver = self.create_solver_agent()

    def init_execution_tool(self):
        if self.executor_name == "Search Executor":
            execution_tool = SearchExecutionTool()
            return execution_tool
        elif self.executor_name == "Web Executor":
            execution_tool = WebExecutionTool()

            # *啟動瀏覽器初始化執行緒
            self.create_browser_thread = threading.Thread(
                target=execution_tool.create_browser,
                daemon=True  # 確保主程式結束時，執行緒也會結束
            )
            self.create_browser_thread.start()

            return execution_tool
        else:
            raise ValueError("Invalid Executor name. Choose 'Search Executor' or 'Web Executor'.")

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
        executor = AgentFactory.create_react_agent_with_yaml(self.executor_name, self.tool.tool_dict)
        return executor

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
    
    def wait_browser_init(self):
        if self.create_browser_thread.is_alive():
            print("browser is starting...")
            self.create_browser_thread.join()
        print("browser is ready")

class EvaluationAgent():
    class EvaluatorResponse(BaseModel):
        """Return a list of score for each step in order."""

        scores: List[float] = Field(
            description="A list of scores for each step in order.",
        )

    def __init__(self):
        self.tool = EvaluationTool()
        self.critic = self.create_critic_agent()
        self.evaluator = self.create_evaluator_agent()

    def create_critic_agent(self):
        critic = AgentFactory.create_react_agent_with_yaml("Critic", self.tool.tool_dict)
        return critic
    
    def create_evaluator_agent(self):
        evaluator = AgentFactory.create_react_agent_with_yaml("Evaluator", self.tool.tool_dict, self.EvaluatorResponse)
        return evaluator

class EvolutionAgent():
    def __init__(self):
        self.tool = EvolutionTool()
        self.analyzer = self.create_analyzer_agent()
        self.prompt_optimizer = self.create_prompt_optimizer_agent()

    def create_analyzer_agent(self):
        analyzer = AgentFactory.create_react_agent_with_yaml("Analyzer", self.tool.tool_dict)
        return analyzer

    def create_prompt_optimizer_agent(self):
        prompt_optimizer = AgentFactory.create_react_agent_with_yaml("Prompt Optimizer", self.tool.tool_dict)
        return prompt_optimizer
    
    

if __name__ == "__main__":
    import time
    import os
    from dotenv import load_dotenv

    from utils.selenium_controller import SeleniumController

    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

    start_time = time.time()

    # *Test Execution Agent

    # executor_name = "Web Executor" # "Search Executor" or "Web Executor"
    # execution_agent = ExecutionAgent(executor_name)

    # planner = execution_agent.planner
    # executor = execution_agent.executor

    # response = planner.invoke({"user_input": [("user", "Please help me apply leave application.")]})
    # for step in response.steps:
    #     print(step)

    # if execution_agent.executor_name == "Web Executor":
    #     execution_agent.wait_browser_init()
    
    # responses = []

    # responses.append(executor.invoke({"messages": [("user", "Step 1. Navigate to https://cis.ncu.edu.tw/iNCU/stdAffair/leaveRequest")]}))
    # responses.append(executor.invoke({"messages": [("user", "Step 2. function_name: 'input_text_with_label', parameters: '{\"label_text\":\"Account\",\"text\":\"user_account\",\"privacy\":\"Account\"}'")]}))
    # responses.append(executor.invoke({"messages": [("user", "Step 3. function_name: 'input_text_with_label', parameters: '{\"label_text\":\"Password\",\"text\":\"user_password\",\"privacy\":\"Password\"}'")]}))
    # responses.append(executor.invoke({"messages": [("user", "Step 4. function_name: 'click_button_with_text', parameters: '{\"text\":\"Login to Portal\"}'")]}))
    # responses.append(executor.invoke({"messages": [("user", "Step 5. function_name: 'click_button_with_text', parameters: '{\"text\":\"Go to\"}'")]}))
    # responses.append(executor.invoke({"messages": [("user", "Step 6. function_name: 'click_button_with_text', parameters: '{\"text\":\"申請\"}'")]}))

    # for response in responses:
    #     print("Response: " + response["messages"][-1].content)

    # *Test Evaluation Agent
    # evaluation_agent = EvaluationAgent()
    # evaluation_agent.tool.execution_chat_log_path = "Outputs/execution_chat_log.txt" 
    # critic = evaluation_agent.critic
    # evaluator = evaluation_agent.evaluator

    # response = critic.invoke({"messages": [("user", "Please evaluate the performance of execution team.")]})
    # print(response["messages"][-1].content) 

    # *Test Evolution Agent
    evolution_agent = EvolutionAgent()
    evolution_agent.tool.execution_chat_log_path = "Outputs/test/epoch 1/execution_chat_log.txt"
    evolution_agent.tool.evaluation_chat_log_path = "Outputs/test/epoch 1/evaluation_chat_log.txt"
    analyzer = evolution_agent.analyzer
    prompt_optimizer = evolution_agent.prompt_optimizer

    # response = analyzer.invoke({"messages": [("user", "Please analyze the evaluation result of the execution team.")]}) # *測試Analyzer Agent
    # print(response["messages"][-1].content)
    
    analysis = """
- **Step Summary**: Evaluate sufficiency judgment requests and clarifications (multiple attempts)
- **Issue or Weakness**: The Execution Team repeatedly requested the content to be evaluated for sufficiency before providing a judgment, causing delays and indicating inefficiency and lack of proactive content handling.
- **Responsible Agent**: Executor (Search Executor)
- **Justification**: This step involves evaluating the content obtained and making a sufficiency judgment, which is part of executing the plan steps. The repeated requests for content indicate that the Executor did not effectively manage or utilize the retrieved information, leading to delays. Since this is about handling and processing retrieved content, it falls under the Search Executor's responsibility.
- **Suggested Improvement**: The Search Executor should improve content management by better tracking and utilizing already obtained information to avoid redundant requests. They should proactively assess content sufficiency without unnecessary back-and-forth, thus improving efficiency.

No other steps were scored as Partially Met or Not Met, and the fully met steps showed no significant improvement suggestions that indicate clear underperformance.

**Primary Responsible Agent**: Search Executor
**Justification for Final Attribution**: The only partial failure was due to inefficient handling of content during execution, specifically repeated requests for sufficiency evaluation that delayed the process. This is clearly an execution issue rather than planning or replanning.
**Summary of Issues**: The main issue was inefficiency in content handling and evaluation during execution, causing delays. Other steps were fully met with no major problems.
    """
    response = prompt_optimizer.invoke({"messages": [("user", analysis)]}) # *測試Prompt Optimizer Agent
    print(response["messages"][-1].content) 

    end_time = time.time()

    print(f"Execution time: {end_time - start_time} seconds")

    # TODO 清除過程使用Threading
    # if execution_agent.executor_name == "Web Executor":
    #     execution_agent.tool.selenium_controller.clean_containers() # *selenium controller解構子有問題，必須runtime內清除