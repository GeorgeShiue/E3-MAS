from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

@tool
def website_info_retriever(query: str) -> str:
    """Perform RAG retrieval on the website database."""
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
        print("page_content: ", page_content)
        result += "link: " + link + "\n" + page_content + "\n"
    
    return result