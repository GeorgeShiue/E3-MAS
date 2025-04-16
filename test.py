from tools import Tools

# load_dotenv()
# api_key = os.getenv("API_KEY")
# os.environ["OPENAI_API_KEY"] = api_key

tools = Tools()
tool_dict = tools.tool_dict



# agents_prompt_content = tool_dict["read_execution_team_agents_prompt"].invoke(input=None)
# print(agents_prompt_content)

# user_input_and_plan_content = tool_dict["read_user_query_and_plan"].invoke(input=None)
# print(user_input_and_plan_content)

# execution_chat_log_content = tool_dict["read_execution_chat_log"].invoke(input=None)
# for i in range(0, len(execution_chat_log_content), 1000):
#     print(execution_chat_log_content[i:i+1000])

# tool_dict["create_browser"]()

# tool_dict["navigate"]("https://www.google.com")

# tool_dict["screen_shot"]()

# del tools.selenium_controller

# execution_chat_log_content = tool_dict["read_execution_chat_log"].invoke(input=None)
# for i in range(0, len(execution_chat_log_content), 1000):
#     print(execution_chat_log_content[i:i+1000])


import re
import requests
from bs4 import BeautifulSoup
import aiohttp
import asyncio

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

async def crawl_links_async(links, base_url):
    websites = []
    tasks = [process_link(link, base_url, websites) for link in links]
    await asyncio.gather(*tasks)
    return websites

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
        links = soup.find_all('a', href=True) # 找出所有超連結 # TODO 讀取iframe有問題

        websites = asyncio.run(crawl_links_async(links, url))
        print(f"成功獲取 [{url}] 中共{len(websites)}個連結。")

        result = "\n".join([f"[{item['title']}]: [{item['link']}]" for item in websites])
        print(result)
        return result
    else:
        print(f"無法獲取 [{url}] 。HTTP 狀態碼: {response.status_code}")
        return f"無法獲取 [{url}] 。HTTP 狀態碼: {response.status_code}"
    
import time

start_time = time.time()
result = tool_dict["website_links_crawler"].invoke({"link": "https://www.ncu.edu.tw/tw/"})
# website_links_crawler("https://www.ncu.edu.tw/tw/")
end_time = time.time()
execution_time = end_time - start_time

print(f"Execution time: {execution_time} seconds")