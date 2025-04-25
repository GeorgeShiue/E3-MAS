import re
import time
import asyncio
from functools import wraps
from io import BytesIO

import yaml
import requests
import aiohttp
import pdfplumber
from bs4 import BeautifulSoup

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from utils.selenium_controller import SeleniumController



# EXECUTION_CHAT_LOG_FILEPATH = "Docs/execution_chat_log_archive.txt"
# EVALUATION_CHAT_LOG_FILEPATH = "Docs/evaluation_chat_log_archive.txt"

# *Testing
EXECUTION_CHAT_LOG_FILEPATH = "Outputs/execution_chat_log.txt"
EVALUATION_CHAT_LOG_FILEPATH = "Outputs/evaluation_chat_log.txt"

agent_parameter_yaml_path = "agent_parameter_base.yaml"
# executor_name = ""

def set_agent_parameter_yaml_path(path):
    """Set the path of agent_parameter.yaml file."""
    global agent_parameter_yaml_path
    agent_parameter_yaml_path = path

# def set_executor_name(name):
#     """Set the name of executor."""
#     global executor_name
#     executor_name = name

class WebExecutionTool():
    def __init__(self, user_id = "1130"):
        self.selenium_controller = SeleniumController()
        self.current_user_id = user_id
        self.current_file_name = None
        self.current_screenshot_name = None
        self.current_screenshot_count = 0
        self.privacy_info = {
            user_id: {
                'account': '111502026',
                'password': 'Georgeshiue1107'
            },
        }

        def auto_screenshot(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 執行原始函數
                result = func(*args, **kwargs)
                time.sleep(0.5)
                # self.current_screenshot_count += 1
                # self.current_screenshot_name = f"website_screenshot_{self.current_screenshot_count}"
                # self.selenium_controller.screen_shot(self.current_user_id, self.current_screenshot_name)
                # return result
                screen_shot()
            return wrapper

        def screen_shot() -> str:
            """Take a screenshot of the current web page."""
            self.current_screenshot_count += 1
            self.current_screenshot_name = f"website_screenshot_{self.current_screenshot_count}"
            result = self.selenium_controller.screen_shot(self.current_user_id, self.current_screenshot_name)
            return result

        @tool
        @auto_screenshot
        def navigate_with_url(url: str) -> str:
            """Navigate to the specified URL."""
            result = self.selenium_controller.navigate_with_url(self.current_user_id, url)
            return result
        
        @tool
        def get_html_content() -> str:
            """Get the HTML content of the current web page to gain information to be used in the current step."""
            result = self.selenium_controller.get_content(self.current_user_id)
            print("HTML content of the current web page is retrieved.")
            return result

        @tool
        @auto_screenshot
        def input_text_with_label(label_text: str, input_text: str, privacy: str = "None") -> str:
            """
            Inputs text into the input element specified by the text of the label.
            When using this tool to input privacy information such as account or password, the privacy parameter should be set to "Account" or "Password".
            This tool wiill replace the input_text argument with the external information when the privacy parameter is not "None".
            """
            if privacy == "Account":
                input_text = self.privacy_info[self.current_user_id]["account"]
            if privacy == "Password":
                input_text = self.privacy_info[self.current_user_id]["password"]
            result = self.selenium_controller.input_text_with_label(self.current_user_id, label_text, input_text, privacy)
            return result

        @tool
        @auto_screenshot
        def input_text_with_name(name: str, input_text: str, privacy: str = "None") -> str:
            """
            Inputs text into the input element specified by the name.
            When using this tool to input privacy information such as account or password, the privacy parameter should be set to "Account" or "Password".
            This tool will replace the input_text argument with the external information when the privacy parameter is not "None".
            """
            if privacy == "Account":
                input_text = self.privacy_info[self.current_user_id]["account"]
            if privacy == "Password":
                input_text = self.privacy_info[self.current_user_id]["password"]
            result = self.selenium_controller.input_text_with_name(self.current_user_id, name, input_text, privacy)
            return result
        
        @tool
        @auto_screenshot
        def click_button_with_text(button_text: str) -> str:
            """Clicks the button specified by the text of the button."""
            result = self.selenium_controller.click_button_with_text(self.current_user_id, button_text)
            return result

        @tool
        @auto_screenshot
        def click_input_with_label(label_text: str) -> str:
            """
            Clicks the input specified by the text of the label.
            Use case: clicking the checkbox with label.
            """
            result = self.selenium_controller.click_input_with_label(self.current_user_id, label_text)
            return result

        @tool
        @auto_screenshot
        def click_input_with_value(value: str) -> str:
            """Clicks the input specified by the value."""
            result = self.selenium_controller.click_input_with_value(self.current_user_id, value)
            return result

        @tool
        @auto_screenshot
        def click_input_with_id(id: str) -> str:
            """
            Clicks the input specified by the id.
            Use case: clicking the input box without label.
            """
            result = self.selenium_controller.click_input_with_id(self.current_user_id, id)
            return result
        
        @tool
        @auto_screenshot
        def select_dropdown_option(option_text: str) -> str:
            """Selects the dropdown option specified by specified option text."""
            result = self.selenium_controller.select_dropdown_option(self.current_user_id, option_text)
            return result

        @tool
        @auto_screenshot
        def click_span_with_aria_label(aria_label: str, index: str = "1") -> str:
            """
            Clicks the span specified by the Aria Label.
            Use case: clicking date inside the calendar.
            index: the index of the span element to click, set index value based on user's instruction such as "第{index}個".
            """
            result = self.selenium_controller.click_span_with_aria_label(self.current_user_id, aria_label, int(index))
            return result

        @tool
        @auto_screenshot
        def upload_file_with_id(id: str, file_path: str) -> str:
            """Uploads a file from given path to the element specified by the id."""
            result = self.selenium_controller.upload_file_with_id(self.current_user_id, id, file_path)
            return result
        
        self.tool_list = [
            navigate_with_url,
            get_html_content,
            input_text_with_label,
            input_text_with_name,
            click_button_with_text,
            click_input_with_label,
            click_input_with_value,
            click_input_with_id,
            select_dropdown_option,
            click_span_with_aria_label,
            upload_file_with_id,
        ]

        self.tool_dict = {tool.name: tool for tool in self.tool_list}


    def create_browser(self) -> str:
        """Create a new browser session."""
        result = self.selenium_controller.create_browser(self.current_user_id)
        return result

# TODO 可以創建一個All Tools class
class SearchExecutionTool():
    def __init__(self):
        self.tool_list = [
            website_info_retriever,
            website_links_crawler,
            website_reader,
            pdf_reader,
        ]

        # define tool dict from tool list
        self.tool_dict = {tool.name: tool for tool in self.tool_list}

class EvaluationTool():
    def __init__(self):
        self.execution_chat_log_path = ""

        @tool
        def read_user_query_and_plan() -> str:
            """Read user query and plan made by Planner."""
            content = []
            with open(self.execution_chat_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if "Executor:" in line:  # 偵測到 "Executor" 關鍵字時停止
                        break
                    content.append(line)

            print("User query and plan have been retrieved.")
            return ''.join(content)

        @tool
        def read_execution_chat_log() -> str:
            """Read the chat log of execution team."""
            with open(self.execution_chat_log_path, "r", encoding="utf-8") as f:
                content = []
                start = False
                for line in f:
                    if "Executor:" in line:
                        start = True

                    if start:
                        content.append(line)
            
            print("Execution chat log has been retrieved.")
            return ''.join(content)

        self.tool_list = [
            read_user_query_and_plan,
            read_execution_chat_log,
        ]

        # define tool dict from tool list
        self.tool_dict = {tool.name: tool for tool in self.tool_list}

class EvolutionTool():
    def __init__(self):
        self.execution_chat_log_path = ""
        self.evaluation_chat_log_path = ""
        self.executor_name = ""

        @tool
        def read_user_query_and_plan() -> str:
            """Read user query and plan made by Planner."""
            content = []
            with open(self.execution_chat_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if "Executor:" in line:
                        break
                    content.append(line)
                    
            print("User query and plan have been retrieved.")
            return ''.join(content)
            
        @tool
        def read_evaluation_result() -> str:
            """Read the evaluation result of execution team."""
            evaluator_content = []
            is_evaluator_section = False

            with open(self.evaluation_chat_log_path, 'r', encoding='utf-8') as file:
                for line in file:
                    # 檢查是否進入 evaluator: 區段
                    if line.strip().startswith("evaluator:"):
                        is_evaluator_section = True
                        evaluator_content.append(line.split("evaluator:", 1)[-1].strip()) # 擷取 evaluator: 後的內容
                    elif is_evaluator_section:
                        evaluator_content.append(line.strip()) # 如果是 evaluator: 區段，繼續擷取內容

            print("Evaluation result has been retrieved.\n")
            return "\n".join(evaluator_content)

        @tool
        def read_execution_team_agents_prompt(agent_name: str) -> str:
            """Read the specified agent's system prompt. The agent is one of the member in execution team."""
            agents_parameter = read_agent_parameter_yaml()

            if "executor" in agent_name or "Executor" in agent_name:
                agent_name = self.executor_name
            
            print(f"{agent_name} system prompt has been retrieved.")
            return agents_parameter[agent_name]["prompt"]
        
        @tool
        def write_updated_agent_prompt(agent_name: str, updated_prompt: str) -> None:
            """Write the updated system prompt of specified agent to the YAML file."""
            # 調整 executor 名稱
            if "executor" in agent_name.lower():
                agent_name = self.executor_name
            
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

        self.tool_list = [
            read_user_query_and_plan,
            read_evaluation_result,
            read_execution_team_agents_prompt,
            write_updated_agent_prompt,
        ]

        # define tool dict from tool list
        self.tool_dict = {tool.name: tool for tool in self.tool_list}



def read_agent_parameter_yaml():
    """Read the agent_parameter.yaml file and return the content."""
    # with open('agent_parameter.yaml', 'r', encoding="utf-8") as f:
    #     agents_parameter = yaml.safe_load(f)

    with open(agent_parameter_yaml_path, 'r', encoding="utf-8") as f:
        agents_parameter = yaml.safe_load(f)
    
    return agents_parameter

@tool
def website_info_retriever(query: str) -> str:
    """Based on user's query perform RAG retrieval on the website information database."""
    print(f"Query: {query}")
    print("---")

    vectorstore = Chroma(
        embedding_function=OpenAIEmbeddings(),
        collection_name="ncu_office_websites",
        persist_directory="Parse Websites v2/ncu_office_websites"
    )

    website_retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})
    docs = website_retriever.invoke(query)

    result = ""
    for i in range(len(docs)):
        link = docs[i].metadata.get("link")
        page_content = docs[i].page_content

        print("link: ", link)
        print("page_content: \n", page_content)
        result += "link: " + link + "\n" + page_content + "\n"
    
    return result

async def process_link(link, url, websites: list):
    title = link.get_text(strip=True)
    if title == '':
        print(f"無法獲取連結標題，跳過連結: {link}")
        return

    href = link.get('href')
    if not href:
        print(f"無法獲取連結網址，跳過連結: {link}")
        return

    final_url = ""

    if 'http' in href:
        final_url = href
    else:
        postclitics = ['html', 'htm', 'asp', 'php', 'pdf', 'PDF']
        url_postclitic = next((p for p in postclitics if p in url), "")
        psotclitic = any(p in href for p in postclitics)

        temp_url = re.sub(rf'/[^/]+\.{url_postclitic}$', '', url) if psotclitic and url_postclitic else url
        href = '/' + href.lstrip('/')
        if temp_url.split('/')[-1] == href.split('/')[1]:
            temp_url = '/'.join(temp_url.split('/')[:-1])
        final_url = temp_url + href

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(final_url, timeout=3, ssl=False) as response:
                if response.status == 200:
                    encoding = response.charset or 'utf-8'
                    websites.append({'title': title, 'link': final_url}) # 連結測試回應成功，加入爬取清單
                else:
                    print(f"[{title}]: [{final_url}]測試回應失敗，不加入爬取清單，HTTP 狀態碼: {response.status}")
    except Exception as e:
        print(f"[{title}]: [{final_url}]測試回應失敗，不加入爬取清單，錯誤: {e}")

async def crawl_links_async(links, base_url):
    websites = []
    tasks = [process_link(link, base_url, websites) for link in links]
    await asyncio.gather(*tasks)
    return websites

@tool
def website_links_crawler(link: str) -> str:
    """Takes url of a website and reads the HTML content of the website and then extracts all the links on that website."""
    extract_link = re.search(r'(https?://[^\]]+)', link)
    url = extract_link.group(1) if extract_link else None
    
    try:
        response = requests.get(url, verify=False, timeout=1)
        encoding = response.apparent_encoding
        response.encoding = encoding
    except requests.exceptions.RequestException as e:
        print(f"無法獲取 [{url}] 。錯誤: {e}")
        return f"Can not access [{url}] . Error: {e}"

    websites = []
    result = ""
    if response.status_code == 200:
        page_content = response.text
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all('a', href=True) # 找出所有超連結 # TODO 讀取iframe有問題

        print(page_content)
        print(len(links))

        websites = asyncio.run(crawl_links_async(links, url))
        # websites = await crawl_links_async(links, url)
        print(f"成功獲取 [{url}] 中共{len(websites)}個連結。")

        result = "\n".join([f"[{item['title']}]: [{item['link']}]" for item in websites])
        print(result)
        return result
    else:
        print(f"無法獲取 [{url}] 。HTTP 狀態碼: {response.status_code}")
        return f"Can not access [{url}] . HTTP status code: {response.status_code}"

@tool
def website_reader(url: str) -> str:
    """Takes url of a website and read the HTML content of a website."""
    try: 
        response = requests.get(url, verify=False)
        encoding = response.apparent_encoding
        response.encoding = encoding
    except requests.exceptions.RequestException as e:
        print(f"無法獲取 [{url}] 。錯誤: {e}")
        return f"Can not access [{url}] . Error: {e}"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.get_text()
    cleaned_content = "\n".join([line for line in content.split("\n") if line.strip()])
    
    print(f"成功讀取 [{url}] 內文：\n{cleaned_content}")
    return cleaned_content

@tool
def pdf_reader(url: str) -> str:
    """Takes url of a PDF file and read the content of a PDF file."""
    try: 
        response = requests.get(url)
        encoding = response.apparent_encoding
        response.encoding = encoding
    except requests.exceptions.RequestException as e:
        print(f"無法獲取PDF。錯誤: {e}")
        return f"Can not access PDF. Error: {e}"

    if response.status_code == 200:
        pdf_file = BytesIO(response.content)
        
        with pdfplumber.open(pdf_file) as pdf:
            pdf_text = ""
            for page in pdf.pages:
                pdf_text += page.extract_text()

        print(f"成功讀取 [{url}] 內文：\n{pdf_text}")
        return pdf_text
    else:
        print(f"PDF下載失敗，HTTP 狀態碼: {response.status_code}")
        return f"PDF download failed, HTTP status code: {response.status_code}"



if __name__ == "__main__":
    # result = read_user_query_and_plan.invoke(input=None)
    # print(result)
    # print()
    # result = read_execution_chat_log.invoke(input=None)
    # print(result)

    website_links_crawler.invoke("http://www.ncu.edu.tw")
    website_links_crawler.invoke("https://pdc.adm.ncu.edu.tw")