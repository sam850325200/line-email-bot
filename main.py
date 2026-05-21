from fastapi import FastAPI, File, UploadFile, Request
from fastapi.staticfiles import StaticFiles
import os
import fitz  
import requests
import urllib.parse  # 用來處理檔名中的中文和空白，轉成安全的網址

app = FastAPI()

UPLOAD_DIR = "temp_uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# [新增] 讓轉運站對外開啟一個「展示窗」，讓 LINE 可以透過網址來拿圖片
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# ⚠️ 請將這裡替換成你剛剛測試成功的 Token 與 User ID
LINE_TOKEN = "+5KTKnXCdDKkzuu2JmUPtXne7qKo99PH0UJS0KQx24H/lUAnGheoIHTegJnWi0UYLb0iFHkDN6egB7UlPNZ8pRnX1+Ie0cN7+uxvQnhZ3mjxqhqJ02wpit0v7ZK91PhEADPAP86KEshV42nCIzrizAdB04t89/1O/w1cDnyilFU="
USER_ID = "C1cf4c9655cd8eb863d5f7a5f5b8153c3"

@app.post("/webhook/receive-pdf")
async def receive_pdf(request: Request, file: UploadFile = File(...)):
    # 1. 存下 PDF
    if not file.filename.endswith(".pdf"):
        return {"status": "error", "message": "只能接收 PDF 檔案"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # 2. PDF 轉圖檔
    pdf_document = fitz.open(file_path)
    
    # 抓取未來雲端主機的專屬網址，並去除結尾多餘的斜線
    base_url = str(request.base_url).rstrip("/") 
    
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    messages = []
    
    # 為了避免 PDF 太多頁被 LINE 拒絕（LINE 規定一次最多發 5 張圖），設定上限 5 頁
    max_pages = min(len(pdf_document), 5)
    
    for page_num in range(max_pages):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=200) 
        
        image_filename = f"{file.filename.replace('.pdf', '')}_page_{page_num + 1}.jpg"
        image_path = os.path.join(UPLOAD_DIR, image_filename)
        pix.save(image_path)
        
        # [新增] 組裝這張圖片的公開網址 (把中文檔名轉換成安全格式)
        safe_filename = urllib.parse.quote(image_filename)
        image_url = f"{base_url}/static/{safe_filename}"
        
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })
        
    pdf_document.close()
    
    # 3. [新增] 將圖片網址清單打包，送給 LINE 伺服器
    data = {
        "to": USER_ID,
        "messages": messages
    }
    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
    
    return {"status": "success", "message": f"成功轉發 {max_pages} 張圖片至 LINE"}
