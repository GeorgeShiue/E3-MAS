import re
import os
import json
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from io import BytesIO
import pdfplumber

load_dotenv()
api_key = os.getenv("API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

def website_crawler(response, url):
    """Takes url of a website and reads the HTML content of the website and then extracts all the links on that website."""
    websites = []
    page_content = response.text # 獲取頁面的HTML內容
    soup = BeautifulSoup(page_content, 'html.parser')
    links = soup.find_all('a')

    # 提取每個<a>標籤的title和href屬性，並組織成列表
    for link in links:
        title = link.get_text(strip=True)  # 提取連結的文本作為標題
        if title == '':  # 若標題為空，則跳過
            continue

        href = link.get('href') # 提取連結的href屬性
        if href: # 確保href存在
            final_url = ""
            # * 包含pdf連結
            # if ('pdf' in href) or ('PDF' in href): # 忽略pdf連結
            #     continue
            if 'http' in href:  # 如果href是完整的連結，直接使用
                final_url = href
            else:
                postclitics = ['html', 'htm', 'asp', 'php']  # 定義可能的後綴類型
                url_postclitic = next((p for p in postclitics if p in url), "")  # 從url中找到匹配的後綴
                psotclitic = any(p in href for p in postclitics)  # 檢查href中是否有後綴

                temp_url = re.sub(rf'/[^/]+\.{url_postclitic}$', '', url) if psotclitic and url_postclitic else url # 如果href和url都有後綴，從url中去除最後的部分，否則使用原始url
                href = '/' + href.lstrip('/')  # 確保href以單個斜杠開頭
                if temp_url.split('/')[-1] == href.split('/')[1]: # 處理相對連結
                    temp_url = '/'.join(temp_url.split('/')[:-1])
                
                final_url = temp_url + href

            websites.append({'title': title, 'link': final_url})  # 將完整連結加入資料中

    return websites

def summarize_content(content):
    cleaned_content = "\n".join([line for line in content.split("\n") if line.strip()])
    cleaned_content = cleaned_content.replace("{", "{{").replace("}", "}}")
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini")
        prompt = ChatPromptTemplate.from_messages([("human", "請總結以下內容：\n\n{content}")])
        chain = {"content": RunnablePassthrough()} | prompt | llm
        summary = chain.invoke({"content": cleaned_content})
    except Exception as e:
        return f"錯誤: {e}"
    
    return summary.content

def read_and_summarize_pdf(response):
    pdf_file = BytesIO(response.content)
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            pdf_content = ""
            for page in pdf.pages:
                pdf_content += page.extract_text()
    except Exception as e:
        return f"錯誤: {e}"

    if pdf_content == "":
        return "錯誤: 無法讀取PDF內容"

    return summarize_content(pdf_content)
    
def read_and_summarize_website(response):
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.get_text()
    except Exception as e:
        return f"錯誤: {e}"

    return summarize_content(content)

websites_num = 0
json_file = 'office_websites_summary_02_23_25.json'
def BFS(link: str, title: str, layer: int):
    global websites_num
    websites_num += 1
    print(f"正在處理第{websites_num}個網頁")
    try:
        with open(json_file, "r", encoding="utf-8") as file:
            office_websites_summary = json.load(file)
            if not isinstance(office_websites_summary, list):  # 確保現有資料是串列
                raise ValueError("JSON 檔案的內容不是一個串列！")
    except FileNotFoundError: # 如果檔案不存在，初始化為空串列
        office_websites_summary = []
    except json.JSONDecodeError: # 如果檔案格式錯誤，初始化為空串列
        print("JSON 檔案內容不合法，將初始化為空串列")
        office_websites_summary = []

    # 檢查網頁是否已經被讀取過
    processed = False
    for website_info in office_websites_summary:
        if website_info['link'] == link:
            print(f'"[{title}]: [{link}] 已經被讀取過，跳至下一個網頁"')
            processed = True
            break

    # 使用正則表達式擷取連結
    extract_link = re.search(r'(https?://[^\]]+)', link)
    url = extract_link.group(1) if extract_link else None
    
    try:
        # response = requests.get(url, timeout=5)
        response = requests.get(url, verify=False, timeout=5) # 忽略SSL證書錯誤
        encoding = response.apparent_encoding
        response.encoding = encoding
    except requests.exceptions.RequestException as e:
        print(f"無法獲取 [{title}]: [{url}] 。錯誤: {e}")
        return []
    if response.status_code != 200:
        print(f"無法獲取 [{title}]: [{url}] 。錯誤: {response.status_code}")
        return []

    # 讀取網頁並總結內容
    if not processed:
        if 'pdf' in url or 'PDF' in url:
            summary = read_and_summarize_pdf(response)
        else:
            summary = read_and_summarize_website(response)
        
        if "錯誤" in summary:
            print(f"無法總結 [{title}]: [{link}] 。{summary}")
        else:
            website_info = {"title": title, "link": link, "summary": summary}
        
            # 寫入JSON檔案
            office_websites_summary.append(website_info)
            with open(json_file, 'w', encoding="utf-8") as file:
                json.dump(office_websites_summary, file, ensure_ascii=False, indent=4)
            
            print(f'"成功讀取 [{title}]: [{link}] 並總結內容後寫入JSON檔案"')
            print('目前成功處理的網頁總量: ' + str(len(office_websites_summary)))

    # 繼續爬取網頁內的所有連結
    if layer <= 2:
        websites = website_crawler(response, link)
        print(f'"成功爬取 [{title}]: [{link}] 的所有連結"')
        print()
        return websites
    
    return []

# 教務處兩層BFS共約1500個網頁，目前可處理共約525個網頁
# link = "https://pdc.adm.ncu.edu.tw"
# title = "中央大學教務處"

# 學務處兩層BFS共約1850個網頁，目前可處理共約1200個網頁
# link = "https://osa.ncu.edu.tw"
# title = "中央大學學務處"

# 總務處兩層BFS共約1100個網頁，目前可處理共約350個網頁
# link = "https://www.oga.ncu.edu.tw"
# title = "中央大學總務處"

# 研究發展處兩層BFS共約4500個網頁以上
# link = "https://ncu.edu.tw/rd"
# title = "中央大學研究發展處"

# 國際事務處
link = 'https://www.oia.ncu.edu.tw'
title = '中央大學國際事務處'

bfs_websites1 = BFS(link, title, 1)
bfs_websites2 = []
for bfs_website1 in bfs_websites1:
    bfs_websites2.extend(BFS(bfs_website1['link'], bfs_website1['title'], 2))
for bfs_website2 in bfs_websites2:
    BFS(bfs_website2['link'], bfs_website2['title'], 3)

print()
print("BFS完成！")
# office_websites_summary_02_23_25_v2.json: 內含教務處、學務處、總務處、研究發展處資料，包含pdf