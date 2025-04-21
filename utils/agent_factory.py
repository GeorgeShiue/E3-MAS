import os
import sys

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from tool import ExecutionTool, EvaluationTool, EvolutionTool, read_agents_parameter_yaml

class AgentFactory():
    @staticmethod
    def extract_agent_parameter_yaml(agent_name):
        agents_parameter = read_agents_parameter_yaml()

        llm_config = agents_parameter[agent_name]["llm_config"]
        prompt = agents_parameter[agent_name]["prompt"]
        tool_list = agents_parameter[agent_name]["tool_list"]
        
        return llm_config, prompt, tool_list

    @staticmethod
    def print_agent_parameter(agent_name):
        llm_config, prompt, tool_list = AgentFactory.extract_agent_parameter_yaml(agent_name)

        print(f"{agent_name}_llm_config:")
        for key, value in llm_config.items():
            print(f"{key}: {value}")
        print()

        print(f"{agent_name}_prompt: \n{prompt}")
        print()

        if 'none' in tool_list:
            print(f"{agent_name} does not have any tools.")
        else:
            print(f"{agent_name}_tool_list: ")
            for tool in tool_list:
                print(tool)
        print()

    @staticmethod
    def create_react_agent_with_yaml(agent_name, tool_dicts=None, response_format=None):
        llm_config, prompt, tool_list = AgentFactory.extract_agent_parameter_yaml(agent_name)

        # if tool_dicts not provided, look for tools in all tools
        if tool_dicts is None:
            execution_tools = ExecutionTool()
            evaluation_tools = EvaluationTool()
            evolution_tools = EvolutionTool()
        
            tool_dicts = {**execution_tools.tool_dict, **evaluation_tools.tool_dict, **evolution_tools.tool_dict}  # merge all tool dicts
        
        tool_list = [tool_dicts[tool] for tool in tool_list if tool in tool_dicts] # select tools from tool_dicts

        llm = ChatOpenAI(model=llm_config["model"], temperature=llm_config["temperature"])
        agent = create_react_agent(llm, tool_list, prompt=prompt, response_format=response_format)

        AgentFactory.print_agent_parameter(agent_name)

        return agent
    


if __name__ == "__main__":
    # load api key from .env file
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

    import time

    start_time = time.time()

    agent_factory = AgentFactory()
    agent_factory.print_agent_parameter("Executor")

    end_time = time.time()

    print(f"Initialize time: {end_time - start_time} seconds")