from tools import Tools

tools = Tools()
tool_dict = tools.tool_dict

# agents_prompt_content = tool_dict["read_execution_team_agents_prompt"].invoke(input=None)
# print(agents_prompt_content)

# user_input_and_plan_content = tool_dict["read_user_input_and_plan"].invoke(input=None)
# print(user_input_and_plan_content)

execution_chat_log_content = tool_dict["read_execution_chat_log"].invoke(input=None)
for i in range(0, len(execution_chat_log_content), 1000):
    print(execution_chat_log_content[i:i+1000])