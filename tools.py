import re
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import pdfplumber
import yaml
import time
from functools import wraps

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from utils.selenium_controller import SeleniumController



class Tools():
    def __init__(self, user_id = "1130"):
        # self.selenium_controller = SeleniumController()
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

        @tool
        def create_browser() -> str:
            """Create a new browser session."""
            result = self.selenium_controller.create_browser(self.current_user_id)
            return result

        def screen_shot() -> str:
            """Take a screenshot of the current web page."""
            self.current_screenshot_count += 1
            self.current_screenshot_name = f"website_screenshot_{self.current_screenshot_count}"
            result = self.selenium_controller.screen_shot(self.current_user_id, self.current_screenshot_name)
            return result

        @tool
        def navigate(url: str) -> str:
            """Navigate to the specified URL."""
            result = self.selenium_controller.navigate(self.current_user_id, url)
            return result
        
        @tool
        def get_html_content() -> str:
            """Get the HTML content of the current web page."""
            result = self.selenium_controller.get_content(self.current_user_id)
            # print(result)
            return result

        
        @tool
        def input_text_with_label(label_text: str, text: str, privacy: str = "None") -> str:
            """
            Inputs text into the input element specified by the text of the label for the given user_id.
            Replace the text argument with the external information when the privacy parameter is not "None".
            """
            if privacy == "Account":
                text = self.privacy_info[self.current_user_id]["account"]
            if privacy == "Password":
                text = self.privacy_info[self.current_user_id]["password"]
            result = self.selenium_controller.input_text_with_label(self.current_user_id, label_text, text, privacy)
            return result

        
        @tool
        def input_text_with_name(name: str, text: str, privacy: str = "None") -> str:
            """
            Inputs text into the input element specified by the text of the label for the given user_id.
            Replace the text argument with the external information when the privacy parameter is not "None".
            """
            if privacy == "Account":
                text = self.privacy_info[self.current_user_id]["account"]
            if privacy == "Password":
                text = self.privacy_info[self.current_user_id]["password"]
            result = self.selenium_controller.input_text_with_name(self.current_user_id, name, text, privacy)
            return result
        
        
        @tool
        def click_button_with_text(text: str) -> str:
            """Clicks the button specified by the Text for the given user_id."""
            result = self.selenium_controller.click_button_with_text(self.current_user_id, text)
            return result

        
        @tool
        def click_input_with_label(label_text: str) -> str:
            """
            Clicks the input specified by the text of the label for the given user_id.
            Use case: clicking the checkbox with label.
            """
            result = self.selenium_controller.click_input_with_label(self.current_user_id, label_text)
            return result

        
        @tool
        def click_input_with_value(value: str) -> str:
            """Clicks the input specified by the Value for the given user_id."""
            result = self.selenium_controller.click_input_with_value(self.current_user_id, value)
            return result

        
        @tool
        def click_input_with_id(id: str) -> str:
            """
            Clicks the input specified by the ID for the given user_id.
            Use case: clicking the input box without label.
            """
            result = self.selenium_controller.click_input_with_id(self.current_user_id, id)
            return result
        
        
        @tool
        def select_dropdown_option(option_text: str) -> str:
            """Selects the dropdown option specified by its text for the given user_id."""
            result = self.selenium_controller.select_dropdown_option(self.current_user_id, option_text)
            return result

        
        @tool
        def click_span_with_aria_label(aria_label: str, index: str = "1") -> str:
            """
            Clicks the span specified by the Aria Label for the given user_id.
            Use case: clicking date inside the calendar.
            index: the index of the span element to click, set index value based on user's instruction such as "第{index}個".
            """
            result = self.selenium_controller.click_span_with_aria_label(self.current_user_id, aria_label, int(index))
            return result

        
        @tool
        def upload_file_with_id(id: str, file_path: str) -> str:
            """Uploads a file to the element specified by the ID for the given user_id."""
            result = self.selenium_controller.upload_file_with_id(self.current_user_id, id, file_path)
            return result

        def pipeline_instruction_saver(pipeline_instructions: str) -> str:
            """Save the pipeline instructions as a txt file."""
            if self.current_file_name is None:
                # self.current_file_name = input("請輸入pipeline名稱: ")
                self.current_file_name = "test" # for testing
            file_name = self.current_file_name
            file_path = "pipeline response/instructions/" + file_name + ".txt"
            with open(file_path, "a", encoding='utf-8') as file:
                file.write(pipeline_instructions + "\n")
            print(f"{file_name} pipeline instructions saved successfully.")
            return f"{file_name} pipeline instructions saved successfully."

        def pipeline_instruction_extractor(file_name: str) -> str:
            """Extract instructions from a pipeline given by its name."""
            file_path = "pipeline response/instructions/" + file_name + ".txt"
            with open(file_path, "r", encoding='utf-8') as file:
                instruction = file.read()
            print(f"{file_name} pipeline instructions extracted successfully.")
            return instruction
        
        def save_privacy_info() -> str:
            """Save the account and password for the user."""
            account = input("請輸入帳號: ")
            password = input("請輸入密碼: ")
            self.privacy_info[self.current_user_id] = {"account": account, "password": password}
            return "Privacy information saved successfully."



        # ----- Evaluation Team Tools -----
        EXECUTION_CHAT_LOG_FILEPATH = "Docs/execution_chat_log_archive.txt"

        @tool
        def read_user_input_and_plan() -> str:
            """Read user input and plan."""
            content = []
            with open(EXECUTION_CHAT_LOG_FILEPATH, 'r', encoding='utf-8') as f:
                for line in f:
                    if "executor:" in line:  # 偵測到 "executor" 關鍵字時停止
                        break
                    content.append(line)

            return ''.join(content)

        @tool
        def read_execution_chat_log() -> str:
            """Read the chat log of execution team."""
            with open(EXECUTION_CHAT_LOG_FILEPATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                extracted_lines = lines[6:] # 提取指定範圍的行
            # with open("chat_log.txt", "r", encoding="utf-8") as f:
            #     content = f.read()
            return ''.join(extracted_lines)
        
        @tool
        def read_execution_team_agents_prompt(agent_name) -> str:
            """Read the specified agent's system prompt. The agent is one of the member in execution team."""
            with open('agents_parameter.yaml', 'r', encoding="utf-8") as f:
                agents_parameter = yaml.safe_load(f)
            
            return agents_parameter[agent_name]["prompt"]



        # ----- Evoluation Team Tools -----
        EVALUATION_CHAT_LOG_FILEPATH = "Docs/evaluation_chat_log_archive.txt"

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
        def write_updated_agent_prompt(agent_name: str, updated_prompt: str) -> None:
            """Write the updated system prompt of specified agent to the YAML file."""
            
            with open('Outputs/updated_agent_prompt.txt', 'w', encoding="utf-8") as f:
                f.write(f"{agent_name}:\n{updated_prompt}")

            return f"{agent_name} updated prompt saved successfully."



        self.tool_dict = {
            "none": none,
            "website_info_retriever": website_info_retriever,
            "website_links_crawler": website_links_crawler,
            "website_reader": website_reader,
            "pdf_reader": pdf_reader,
            "create_browser": create_browser,
            "screen_shot": screen_shot,
            "navigate": navigate,
            "get_html_content": get_html_content,
            "input_text_with_label": input_text_with_label,
            "input_text_with_name": input_text_with_name,
            "click_button_with_text": click_button_with_text,
            "click_input_with_label": click_input_with_label,
            "click_input_with_value": click_input_with_value,
            "click_input_with_id": click_input_with_id,
            "select_dropdown_option": select_dropdown_option,
            "click_span_with_aria_label": click_span_with_aria_label,
            "upload_file_with_id": upload_file_with_id,
            "read_user_input_and_plan": read_user_input_and_plan,
            "read_execution_chat_log": read_execution_chat_log,
            "read_execution_team_agents_prompt": read_execution_team_agents_prompt,
            "read_evaluation_result": read_evaluation_result,
            "write_updated_agent_prompt": write_updated_agent_prompt,
        }

    # def __del__(self):
    #     del self.selenium_controller
    #     print(f"Browser for user {self.current_user_id} closed.")