import yaml
from typing import Union, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from tools import Tools



# Initialize the tools
tools = Tools()
tool_dict = tools.tool_dict

# print("This app is using the following tool:")
# for tool in tool_dict:
#     print(tool)
# print()



# Define Agent Response Class
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

    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )



# Define Agents

# Load Agents Parameter from YAML file
# ! 注意yaml檔案版本
with open('agents_parameter.yaml', 'r', encoding="utf-8") as file:
    agents_parameter = yaml.safe_load(file)

# Create React Agent
def create_react_agent_with_yaml(agent_name, response_format=None):
    llm_config = agents_parameter[agent_name]["llm_config"]
    prompt = agents_parameter[agent_name]["prompt"]
    tool_list = [tool_dict[name] for name in agents_parameter[agent_name]["tool_list"]]

    llm = ChatOpenAI(model=llm_config["model"], temperature=llm_config["temperature"])
    agent = create_react_agent(llm, tool_list, prompt=prompt, response_format=response_format)

    print(f"{agent_name}_llm_config:")
    for key, value in llm_config.items():
        print(f"{key}: {value}")
    print(f"{agent_name}_prompt: \n" + prompt)
    print(f"{agent_name}_tool_list: ")
    for tool in tool_list:
        print(tool.name)

    return agent

# Define Planner Agent
# * Plannger Agent 使用 ChatPromptTemplate.from_messages() 搭配 with_structured_output(Plan) 實現
planner_llm_config = agents_parameter["Planner"]["llm_config"]
planner_system_prompt = agents_parameter["Planner"]["prompt"]

planner_llm = ChatOpenAI(model=planner_llm_config["model"], temperature=planner_llm_config["temperature"])
planner_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", planner_system_prompt),
        ("placeholder", "{user_input}"), # placeholer 用來動態嵌入使用者輸入的訊息
    ]
)

planner = planner_prompt | planner_llm.with_structured_output(Plan) # 限制使用特定模板回答問題

# print("planner_llm_config:")
# for key, value in planner_llm_config.items():
#     print(f"{key}: {value}")
# print("planner_system_prompt: \n" + planner_system_prompt)

# Define Executor Agent
# * Executor Agent 因為需要取用工具所以使用 create_react_agent() 實現
# executor = create_react_agent_with_yaml("Executor")

# Define Replanner Agent
# * Replanner Agent 使用 ChatPromptTemplate.from_template() 搭配 with_structured_output(Act) 實現
replanner_llm_config = agents_parameter["Replanner"]["llm_config"]
replanner_system_prompt = f"{agents_parameter['Replanner']['prompt']}"

replanner_llm = ChatOpenAI(model=replanner_llm_config["model"], temperature=replanner_llm_config["temperature"]) # ! Replanner需要使用gpt-4o才不會一直call tools
replanner_prompt = ChatPromptTemplate.from_template(replanner_system_prompt)

replanner = replanner_prompt | replanner_llm.with_structured_output(Act) # 限制使用特定模板回答問題

# print("replanner_model: " + replanner_model)
# print("replanner_prompt: \n" + replanner_system_prompt)

# Define Solver Agent
# * Solver Agent 使用 ChatPromptTemplate.from_template() 實現
solver_model = agents_parameter["Solver"]["model"]
solver_system_prompt = agents_parameter["Solver"]["prompt"]

solver_llm = ChatOpenAI(model=solver_model)
solver_prompt = ChatPromptTemplate.from_template(solver_system_prompt)

solver = solver_prompt | solver_llm

# print("solver_model: " + solver_model)
# print("solver_system_prompt: \n" + solver_system_prompt)


# # Define Critic Agent
# critic = create_react_agent_with_yaml("Critic")

# # Define Evaluator Agent
# evaluator = create_react_agent_with_yaml("Evaluator")