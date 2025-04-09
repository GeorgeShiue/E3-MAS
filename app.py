# * 注意是否有動態宣告tools的需要
import asyncio

from graph import app

sequence = 0

with open("chat_log.txt", "w", encoding="utf-8") as f:
    sequence = 0
    f.write("")

def write_to_chat_log(content):
    with open("chat_log.txt", "a", encoding="utf-8") as f:
        f.write(content)

# 定義一個異步函式來執行異步邏輯
async def run_app():
    # Who is the headmaster of National Central University in Taiwan?
    config = {"recursion_limit": 50}
    inputs = {
        "input": "Who is the headmaster of National Central University in Taiwan?",
        "history": [],  # 初始化儲存History的list
    }
    write_to_chat_log(f"User Query:\n{inputs['input']}\n\n")

    async for event in app.astream(inputs, config=config):
        for agent, state in event.items():
            if agent != "__end__":
                global sequence
                sequence += 1
                write_to_chat_log(f"{sequence}. {agent}:\n")

                for key, value in state.items():
                    if key != "history":
                        write_to_chat_log(f"{key}: {value}\n")
                
                write_to_chat_log("\n")

# 使用 asyncio.run() 執行異步函式
if __name__ == "__main__":
    asyncio.run(run_app())