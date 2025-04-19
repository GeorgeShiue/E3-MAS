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



EVALUATION_CHAT_LOG_FILEPATH = "Docs/evaluation_chat_log_archive.txt"
EXECUTION_CHAT_LOG_FILEPATH = "Docs/execution_chat_log_archive.txt"



# TODO 可以創建一個All Tools class
class ExecutionTool():
    def __init__(self):
        # define tool list
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
        # define tool list
        self.tool_list = [
            read_user_query_and_plan,
            read_execution_chat_log,
        ]

        # define tool dict from tool list
        self.tool_dict = {tool.name: tool for tool in self.tool_list}

class EvolutionTool():
    def __init__(self):
        # define tool list
        self.tool_list = [
            read_evaluation_result,
            read_execution_team_agents_prompt,
            write_updated_agent_prompt,
        ]

        # define tool dict from tool list
        self.tool_dict = {tool.name: tool for tool in self.tool_list}

def read_agents_parameter_yaml():
    """Read the agent_parameter.yaml file and return the content."""
    with open('agent_parameter.yaml', 'r', encoding="utf-8") as f:
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

async def process_link(link, url, websites):
    title = link.get_text(strip=True)
    if title == '':
        return

    href = link.get('href')
    if not href:
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
                    websites.append({'title': title, 'link': final_url})
    except Exception as e:
        print(f"無法獲取[{title}]: [{final_url}] ，錯誤: {e}")

async def crawl_links_async(self, links, base_url):
    websites = []
    tasks = [self.process_link(link, base_url, websites) for link in links]
    await asyncio.gather(*tasks)
    return websites

@tool
def website_links_crawler(self, link: str) -> str:
    """Takes url of a website and reads the HTML content of the website and then extracts all the links on that website."""
    extract_link = re.search(r'(https?://[^\]]+)', link)
    url = extract_link.group(1) if extract_link else None
    
    try:
        response = requests.get(url, verify=False, timeout=1)
        encoding = response.apparent_encoding
        response.encoding = encoding
    except requests.exceptions.RequestException as e:
        print(f"無法獲取 [{url}] 。錯誤: {e}")
        return f"無法獲取 [{url}] 。錯誤: {e}"

    websites = []
    result = ""
    if response.status_code == 200:
        page_content = response.text
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all('a', href=True) # 找出所有超連結 # TODO 讀取iframe有問題

        websites = asyncio.run(self.crawl_links_async(links, url))
        # websites = await crawl_links_async(links, url)
        print(f"成功獲取 [{url}] 中共{len(websites)}個連結。")

        result = "\n".join([f"[{item['title']}]: [{item['link']}]" for item in websites])
        print(result)
        return result
    else:
        print(f"無法獲取 [{url}] 。HTTP 狀態碼: {response.status_code}")
        return f"無法獲取 [{url}] 。HTTP 狀態碼: {response.status_code}"

@tool
def website_reader(url: str) -> str:
    """Takes url of a website and read the HTML content of a website."""
    try: 
        response = requests.get(url, verify=False)
        encoding = response.apparent_encoding
        response.encoding = encoding
    except requests.exceptions.RequestException as e:
        print(f"無法獲取 [{url}] 。錯誤: {e}")
        return f"無法獲取 [{url}] 。錯誤: {e}"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.get_text()
    print(f"成功讀取 [{url}] 內文。")

    cleaned_content = "\n".join([line for line in content.split("\n") if line.strip()])
    print(cleaned_content)
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
        return f"無法獲取PDF。錯誤: {e}"

    if response.status_code == 200:
        pdf_file = BytesIO(response.content)
        
        with pdfplumber.open(pdf_file) as pdf:
            pdf_text = ""
            for page in pdf.pages:
                pdf_text += page.extract_text()

        print(f"成功讀取 [{url}] 內文：\n{pdf_text}")
        return pdf_text
    else:
        print(f"下載失敗，HTTP 狀態碼: {response.status_code}")
        return f"下載失敗，HTTP 狀態碼: {response.status_code}"

@tool
def read_user_query_and_plan() -> str:
    """Read user query and plan made by Planner."""
    content = []
    with open(EXECUTION_CHAT_LOG_FILEPATH, 'r', encoding='utf-8') as f:
        for line in f:
            if "executor:" in line:  # 偵測到 "executor" 關鍵字時停止
                break
            content.append(line)

    # print("User input and plan:\n " + ''.join(content))
    return ''.join(content)

@tool
def read_execution_chat_log() -> str:
    """Read the chat log of execution team."""
    with open(EXECUTION_CHAT_LOG_FILEPATH, "r", encoding="utf-8") as f:
        content = []
        start = False
        for line in f:
            if "executor:" in line:
                start = True
            if "solver:" in line:
                start = False

            if start:
                content.append(line)
    
    # print("Execution chat log:\n " + ''.join(content))
    return ''.join(content)

@tool
def read_evaluation_result():
    """Read the evaluation result of execution team."""
    evaluator_content = []
    is_evaluator_section = False

    with open(EVALUATION_CHAT_LOG_FILEPATH, 'r', encoding='utf-8') as file:
        for line in file:
            # 檢查是否進入 evaluator: 區段
            if line.strip().startswith("evaluator:"):
                is_evaluator_section = True
                evaluator_content.append(line.split("evaluator:", 1)[-1].strip()) # 擷取 evaluator: 後的內容
            elif is_evaluator_section:
                evaluator_content.append(line.strip()) # 如果是 evaluator: 區段，繼續擷取內容

    return "\n".join(evaluator_content)

@tool
def read_execution_team_agents_prompt(agent_name) -> str:
    """Read the specified agent's system prompt. The agent is one of the member in execution team."""
    agents_parameter = read_agents_parameter_yaml()
    
    return agents_parameter[agent_name]["prompt"]

@tool
def write_updated_agent_prompt(agent_name: str, updated_prompt: str) -> None:
    """Write the updated system prompt of specified agent to the YAML file."""
    
    with open('Outputs/updated_agent_prompt.txt', 'w', encoding="utf-8") as f:
        f.write(f"{agent_name}:\n{updated_prompt}")

    return f"{agent_name} updated prompt saved successfully."



if __name__ == "__main__":
    agents_parameter = read_agents_parameter_yaml()

    print(agents_parameter)