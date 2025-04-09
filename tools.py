import re
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import pdfplumber
import yaml

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


class Tools():
    def __init__(self):
        @tool
        def none() -> None:
            """Return None."""
            return None


        # ----- Execution Team Tools -----
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
                return f"無法獲取 [{url}] 。錯誤: {e}"

            websites = []
            result = ""
            if response.status_code == 200:
                page_content = response.text
                soup = BeautifulSoup(page_content, 'html.parser')
                links = soup.find_all('a') # 找出所有超連結 # TODO 讀取iframe有問題

                for link in links:
                    title = link.get_text(strip=True)  # 提取連結的文字作為標題
                    if title == '':
                        continue

                    href = link.get('href') # 提取連結的href屬性
                    if href:
                        final_url = ""

                        if 'http' in href:  # 如果href由http開頭，直接使用
                            final_url = href
                        else:
                            postclitics = ['html', 'htm', 'asp', 'php', 'pdf', 'PDF']  # 定義可能的後綴類型
                            url_postclitic = next((p for p in postclitics if p in url), "")  # 從url中找到匹配的後綴
                            psotclitic = any(p in href for p in postclitics)  # 檢查href中是否有後綴

                            # 如果href和url都有後綴，從url中去除最後的部分，否則使用原始url
                            temp_url = re.sub(rf'/[^/]+\.{url_postclitic}$', '', url) if psotclitic and url_postclitic else url
                            href = '/' + href.lstrip('/')  # 確保href以單個斜杠開頭
                            if temp_url.split('/')[-1] == href.split('/')[1]: # 處理相對連結
                                temp_url = '/'.join(temp_url.split('/')[:-1])
                            
                            final_url = temp_url + href

                        try: # 檢查組合後的連結是否有效
                            test_response = requests.get(final_url, verify=False, timeout=1)
                            encoding = test_response.apparent_encoding
                            test_response.encoding = encoding
                            if test_response.status_code == 200:
                                # print(f"成功獲取[{title}]: [{final_url}] ，加入資料中。")
                                websites.append({'title': title, 'link': final_url})
                            # else:
                                # print(f"無法獲取[{title}]: [{final_url}] ，不加入資料中。HTTP 狀態碼: {test_response.status_code}")
                        except requests.exceptions.RequestException as e:
                            print(f"無法獲取[{title}]: [{final_url}] ，不加入資料中。錯誤: {e}")

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
            print(f"成功讀取 [{url}] 並總結。")

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
                print(f"無法獲取網頁。錯誤: {e}")
                return f"無法獲取網頁。錯誤: {e}"

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
        


        # ----- Evaluation Team Tools -----
        CHAT_LOG_FILEPATH = "Docs/chat_log_archive.txt"

        @tool
        def read_user_input_and_plan() -> str:
            """Read user input and plan."""
            with open(CHAT_LOG_FILEPATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                extracted_lines = lines[0:5] # 提取指定範圍的行
            return ''.join(extracted_lines)

        @tool
        def read_execution_chat_log() -> str:
            """Read the chat log of execution team."""
            with open(CHAT_LOG_FILEPATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                extracted_lines = lines[6:] # 提取指定範圍的行
            # with open("chat_log.txt", "r", encoding="utf-8") as f:
            #     content = f.read()
            return ''.join(extracted_lines)
        
        @tool
        def read_execution_team_agents_prompt() -> str:
            """Read the agents prompt of execution team."""
            with open('agents_parameter.yaml', 'r', encoding="utf-8") as f:
                agents_parameter = yaml.safe_load(f)
            
            for agent in agents_parameter:
                print(agent + " Prompt:")
                print(agents_parameter[agent]["prompt"])
                print()



        self.tool_dict = {
            "none": none,
            "website_info_retriever": website_info_retriever,
            "website_links_crawler": website_links_crawler,
            "website_reader": website_reader,
            "pdf_reader": pdf_reader,
            "read_user_input_and_plan": read_user_input_and_plan,
            "read_execution_chat_log": read_execution_chat_log,
            "read_execution_team_agents_prompt": read_execution_team_agents_prompt,
        }

        

# -----tool testing field-----

# tools = Tools()

# import os
# from dotenv import load_dotenv

# load_dotenv()
# api_key = os.getenv("API_KEY")
# os.environ["OPENAI_API_KEY"] = api_key

# website_info_retriever = tools.tool_dict["website_info_retriever"]
# print(website_info_retriever)
# response = website_info_retriever.invoke("請幫我找學務處最新消息")
# print(response)

# website_links_crawler = tools.tool_dict["website_links_crawler"]
# print(website_links_crawler)
# response = website_links_crawler.invoke("https://www.ncu.edu.tw/tw/index.html")
# print(response)