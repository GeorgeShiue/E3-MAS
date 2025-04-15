from tools import Tools

# load_dotenv()
# api_key = os.getenv("API_KEY")
# os.environ["OPENAI_API_KEY"] = api_key

tools = Tools()
tool_dict = tools.tool_dict



# agents_prompt_content = tool_dict["read_execution_team_agents_prompt"].invoke(input=None)
# print(agents_prompt_content)

# user_input_and_plan_content = tool_dict["read_user_input_and_plan"].invoke(input=None)
# print(user_input_and_plan_content)

# execution_chat_log_content = tool_dict["read_execution_chat_log"].invoke(input=None)
# for i in range(0, len(execution_chat_log_content), 1000):
#     print(execution_chat_log_content[i:i+1000])

# tool_dict["create_browser"]()

# tool_dict["navigate"]("https://www.google.com")

# tool_dict["screen_shot"]()

# del tools.selenium_controller

import yaml

def read_execution_team_agents_prompt(agent_name) -> str:
    """Read the specified agent's system prompt. The agent is one of the member in execution team."""
    with open('agents_parameter.yaml', 'r', encoding="utf-8") as f:
        agents_parameter = yaml.safe_load(f)
    
    return agents_parameter[agent_name]["prompt"]

print(read_execution_team_agents_prompt("Replanner"))


# del tools.selenium_controller