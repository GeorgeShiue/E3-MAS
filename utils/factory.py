import os
import sys
from io import BytesIO
from PIL import Image

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from tool import SearchExecutionTool, WebExecutionTool, EvaluationTool, EvolutionTool, read_agent_parameter_yaml

class AgentFactory():
    @staticmethod
    def extract_agent_parameter_yaml(agent_name):
        agents_parameter = read_agent_parameter_yaml()

        llm_config = agents_parameter[agent_name]["llm_config"]
        prompt = agents_parameter[agent_name]["prompt"]
        tool_list = agents_parameter[agent_name]["tool_list"]
        
        return llm_config, prompt, tool_list

    @staticmethod
    def print_agent_parameter(agent_name):
        llm_config, prompt, tool_list = AgentFactory.extract_agent_parameter_yaml(agent_name)

        print(f"{agent_name}_llm_config:")
        for key, value in llm_config.items():
            print(f"    {key}: {value}")
        print()

        print(f"{agent_name}_prompt:\n  {prompt}")
        print()

    @staticmethod
    def create_react_agent_with_yaml(agent_name, tool_dicts=None, response_format=None):
        llm_config, prompt, tool_list = AgentFactory.extract_agent_parameter_yaml(agent_name)

        # if tool_dicts not provided, look for tools in all tools
        if tool_dicts is None:
            search_execution_tool = SearchExecutionTool()
            web_execution_tool = WebExecutionTool()
            evaluation_tool = EvaluationTool()
            evolution_tool = EvolutionTool()
        
            tool_dicts = {**search_execution_tool.tool_dict, **web_execution_tool.tool_dict, **evaluation_tool.tool_dict, **evolution_tool.tool_dict}  # merge all tool dicts
        
        selected_tool_list = [tool_dicts[tool] for tool in tool_list if tool in tool_dicts] # select tools from tool_dicts

        llm = ChatOpenAI(model=llm_config["model"], temperature=llm_config["temperature"])
        agent = create_react_agent(llm, selected_tool_list, prompt=prompt, response_format=response_format)

        AgentFactory.print_agent_parameter(agent_name) # print llm_config, prompt

        # print selected tools
        if 'none' in selected_tool_list:
            print(f"{agent_name} does not have any tools.")
        else:
            print(f"{agent_name}_tool_list: ")
            for tool in selected_tool_list:
                print(f"    {tool.name}")
        print()

        return agent

class GraphFactory():
    @staticmethod
    def save_graph_mermaid(app: CompiledStateGraph, graph_name): # TODO 可以歸入utils

        graph_bytes = app.get_graph(xray=True).draw_mermaid_png()
        
        # save to Outputs folder
        output_file_path = os.path.join("Outputs", graph_name) + ".png"
        with BytesIO(graph_bytes) as byte_stream:
            image = Image.open(byte_stream)
            image.save(output_file_path, format="PNG")
        
        print(f"Graph mermaid image saved to: {output_file_path}")


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