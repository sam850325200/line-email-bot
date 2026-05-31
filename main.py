from fastapi import FastAPI, File, UploadFile, Request
from fastapi.staticfiles import StaticFiles
import os
import fitz  
import requests
import urllib.parse 

app = FastAPI()

UPLOAD_DIR = "temp_uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# ⚠️ 請將這裡替換成你剛剛測試成功的 Token 與 群組 User ID
LINE_TOKEN = "+5KTKnXCdDKkzuu2JmUPtXne7qKo99PH0UJS0KQx24H/lUAnGheoIHTegJnWi0UYLb0iFHkDN6egB7UlPNZ8pRnX1+Ie0cN7+uxvQnhZ3mjxqhqJ02wpit0v7ZK91PhEADPAP86KEshV42nCIzrizAdB04t89/1O/w1cDnyilFU="
USER_ID = "C1cf4c9655cd8eb863d5f7a5f5b8153c3"

# 💡 [修改] 我們把網址名稱從 receive-pdf 改成了通用的 receive-file
@app.post("/webhook/receive-file")
async def receive_file(request: Request, file: UploadFile = File(...)):
    # 1. 把 GAS 傳來的檔案存進 temp_uploads 資料夾
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # 抓取未來雲端主機的專屬網址
    base_url = str(request.base_url).rstrip("/") 
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    messages = []
    
    # 💡 [新增] 判斷檔名類型，決定走哪一條路線
    filename_lower = file.filename.lower()
    
    # 【路線 A：如果是 PDF 檔案】
    if filename_lower.endswith(".pdf"):
        pdf_document = fitz.open(file_path)
        max_pages = min(len(pdf_document), 5)
        
        for page_num in range(max_pages):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(dpi=200) 
            
            image_filename = f"{file.filename.replace('.pdf', '')}_page_{page_num + 1}.jpg"
            image_path = os.path.join(UPLOAD_DIR, image_filename)
            pix.save(image_path)
            
            safe_filename = urllib.parse.quote(image_filename)
            image_url = f"{base_url}/static/{safe_filename}"
            
            messages.append({
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            })
            
        pdf_document.close()
        
    # 【路線 B：如果是圖片檔案 (信件內文圖片)】
    elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
        safe_filename = urllib.parse.quote(file.filename)
        image_url = f"{base_url}/static/{safe_filename}"
        
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })
        
    # 如果都不是，直接退回
    else:
        return {"status": "error", "message": "只能接收 PDF 或圖片檔案"}
    
    # 3. 將圖片網址清單打包，送給 LINE 伺服器
    if messages:
        data = {
            "to": USER_ID,
            "messages": messages
        }
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
    
    return {"status": "success", "message": "檔案已成功轉發至 LINE"}
