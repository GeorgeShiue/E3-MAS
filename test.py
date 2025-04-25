from ruamel.yaml import YAML

agent_parameter_yaml_path = "agent_parameter_test.yaml"

def write_updated_agent_prompt(agent_name: str, updated_prompt: str) -> None:
    """Write the updated system prompt of specified agent to the YAML file."""
    # 調整 executor 名稱
    # if "executor" in agent_name.lower():
    #     agent_name = self.executor_name
    
    # 讀取文件內容
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    
    with open(agent_parameter_yaml_path, 'r', encoding="utf-8") as f:
        agent_parameter = yaml.load(f)
    
    # 更新提示文字
    agent_parameter[agent_name]["prompt"] = updated_prompt
    
    # 寫回文件
    with open(agent_parameter_yaml_path, 'w', encoding="utf-8") as f:
        yaml.dump(agent_parameter, f)
    
    print(f"{agent_name} updated prompt saved successfully.\n")
    return f"{agent_name} updated prompt saved successfully."


write_updated_agent_prompt("Planner", "This is the updated prompt for Planner.")