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

user_input_and_plan_content = tool_dict["read_user_input_and_plan"].invoke(input=None)
print(user_input_and_plan_content)