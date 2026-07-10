from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF 套件
import base64

app = FastAPI()

# 💡 專屬轉檔端點：接收 GAS 傳來的 PDF，傳回 JPG 的 Base64 文字清單
@app.post("/webhook/pdf-to-jpg")
async def pdf_to_jpg(file: UploadFile = File(...)):
    # 讀取 GAS 傳過來的 PDF 檔案
    content = await file.read()
    
    # 打開 PDF
    pdf_document = fitz.open(stream=content, filetype="pdf")
    pages_base64 = []
    
    # 逐頁將 PDF 轉換為 JPG 圖片，並轉成文字編碼
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=200) 
        img_bytes = pix.tobytes("jpg") 
        
        base64_string = base64.b64encode(img_bytes).decode("utf-8")
        
        pages_base64.append({
            "filename": f"{file.filename.replace('.pdf', '')}_page_{page_num + 1}.jpg",
            "base64_data": base64_string
        })
        
    pdf_document.close()
    
    # 將切好的圖片包裝送回給 GAS
    return {"pages": pages_base64}
