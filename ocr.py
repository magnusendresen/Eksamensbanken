import os
import asyncio
from google.cloud import vision
import fitz 

json_path = os.getenv("OCRACLE_JSON_PATH")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_path
if not json_path:
    raise ValueError("OCRACLE_JSON_PATH environment variable not set.")
client = vision.ImageAnnotatorClient()

async def run_in_threads(func, items):
    tasks = [asyncio.to_thread(func, item) for item in items]
    return await asyncio.gather(*tasks)

def page_to_img_bytes(page) -> bytes:
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes()

def ocr_image(img: bytes) -> str:
    try:
        image = vision.Image(content=img)
        response = client.text_detection(image=image)
        return response.text_annotations
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        return ""
    