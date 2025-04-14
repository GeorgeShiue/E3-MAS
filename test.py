from tools import Tools

# load_dotenv()
# api_key = os.getenv("API_KEY_SELF")
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



def extract_evaluator_content(file_path):
    """
    從聊天紀錄中擷取 evaluator: 後的所有文字內容。
    
    :param file_path: 聊天紀錄檔案的路徑
    :return: 包含所有 evaluator: 後文字內容的字串
    """
    evaluator_content = []
    is_evaluator_section = False

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 檢查是否進入 evaluator: 區段
            if line.strip().startswith("evaluator:"):
                is_evaluator_section = True
                # 擷取 evaluator: 後的內容
                evaluator_content.append(line.split("evaluator:", 1)[-1].strip())
            elif is_evaluator_section:
                # 如果是 evaluator: 區段，繼續擷取內容
                evaluator_content.append(line.strip())

    return "\n".join(evaluator_content)



file_path = "Docs\\evaluation_chat_log_archive.txt"
evaluator_text = extract_evaluator_content(file_path)
print(evaluator_text)



# del tools.selenium_controller