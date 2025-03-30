import requests
import pdfplumber
from io import BytesIO

url = 'https://pdc.adm.ncu.edu.tw/postM/post/reg/1140117_2.pdf'

response = requests.get(url, timeout=5)
encoding = response.apparent_encoding
response.encoding = encoding

pdf_file = BytesIO(response.content)

with pdfplumber.open(pdf_file) as pdf:
    pdf_content = ""
    for page in pdf.pages:
        pdf_content += page.extract_text()

print(pdf_content)
print("len:" + str(len(pdf_content)))