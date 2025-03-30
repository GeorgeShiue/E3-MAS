import os
import json
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
api_key = os.getenv("API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

# 準備數據
data = []
with open("office_websites_summary_02_23_25.json", "r", encoding='utf-8') as file:
    data = json.load(file)

# 將數據轉換為 Document 格式
documents = [
    Document(
        page_content="網站標題: " + item["title"] + "\n簡介: " + item["summary"] + "\n---",
        metadata={"link": item["link"]}
    )
    for item in data
]

# 使用 LangChain 的文本分割工具
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
split_documents = text_splitter.split_documents(documents)

# 構建向量資料庫
vectorstore = Chroma.from_documents(
    documents = split_documents, 
    embedding = OpenAIEmbeddings(),
    collection_name = "ncu_office_websites",
    persist_directory = "./ncu_office_websites"
)

print("vector store 構建完成！")