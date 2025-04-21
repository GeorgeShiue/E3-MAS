from typing import List, Union

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from tool import ExecutionTool

from utils.agent_factory import AgentFactory



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
        self.execution_tools = ExecutionTool()
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
        executor = AgentFactory.create_react_agent_with_yaml("Executor", self.execution_tools.tool_dict)
        return executor
    
    def create_web_executor_agent(self):
        web_executor = AgentFactory.create_react_agent_with_yaml("Web Executor", self.execution_tools.tool_dict)
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
    # Load environment variables from .env file
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key    

    import time

    start_time = time.time()

    execution_agent = ExecutionAgent()
    # evaluation_agent = EvaluationAgent()
    # evolution_agent = EvolutionAgent()

    end_time = time.time()

    print(f"Initialize time: {end_time - start_time} seconds")