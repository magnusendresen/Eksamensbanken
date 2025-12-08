import os
import time
import tkinter as tk
from tkinter import filedialog
from openai import OpenAI
import fitz
import pytesseract
from PIL import Image
from io import BytesIO
from prompt_llm import prompt_llm, PROMPT_CONFIG
from ocr import ocr_image, page_to_img_bytes, run_in_threads

class Exam:
    def __init__(self, exam: str):
        self.pdf = Pdf(f"{exam}.pdf")
        self.parsed_text = ""
        self.ocr_text = ""

    # Temporary logic for loading existing data
        if not os.path.exists(f"{exam}_parsed.txt"):
            print() # Gather parsed text
        elif os.path.exists(f"{exam}_parsed.txt"):
            with open(f"{exam}_parsed.txt", "r", encoding="utf-8") as f:
                self.parsed_text = f.read()

        if not os.path.exists(f"{exam}_ocr.txt"):
            print() # Gather OCR text
        elif os.path.exists(f"{exam}_ocr.txt"):
            with open(f"{exam}_ocr.txt", "r", encoding="utf-8") as f:
                self.ocr_text = f.read()


class Pdf:
    def __init__(self, path: str):
        self.path = path
        self.doc = fitz.open(path)
        self.pages = []
        self.blocks = []
        self.ocr_text = ""
        
        for i, page in enumerate(self.doc):
            self.pages.append(Page(self, page, i))
            self.ocr_text += str(self.pages[i].ocr_text) + "\n"

        self.blocks = [block for page in self.pages for block in page.blocks]
        print(f"Loaded PDF. Summary: {len(self.pages)} pages, {len(self.blocks)} blocks ({sum(b.type == 1 for b in self.blocks)} images and {sum(b.type == 0 for b in self.blocks)} text), {len(self.ocr_text)} characters from OCR.")

class Page:
    def __init__(self, pdf, page, page_number: int):
        self.pdf = pdf
        self.page = page
        self.page_number = page_number
        self.blocks = []
        self.ocr_text = ocr_image(page_to_img_bytes(page))

        for i, block in enumerate(page.get_text("dict")["blocks"]):
            self.blocks.append(Bbox(pdf, self, block, i))

class Bbox:
    def __init__(self, pdf, page, block, block_number: int):
        self.pdf = pdf
        self.page = page
        self.block_number = block_number
        self.type = block["type"]

        self.top = block["bbox"][1]
        self.bottom = block["bbox"][3]

def select_pdf():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf")]
    )
    return file_path

def parse_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def parse_pdf_blocks(pdf_path: str) -> str:
    pdf = fitz.open(pdf_path)
    parsed_text = ""
    block_counter = 0

    for page in pdf:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            block_type = block.get("type")
            block_type_str = "IMAGE" if block_type == 1 else "TEXT"
            block_title = f"BLOCK {block_counter} | TYPE: {block_type_str}"
            parsed_text += block_title + "\n"

            if block_type == 0: # text block
                block_text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text += span.get("text", "")
                parsed_text += block_text + "\n"
            elif block_type == 1: # image block
                x0, y0, x1, y1 = block["bbox"]
                pix = page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1))
                img_data = pix.tobytes("png")
                image = Image.open(BytesIO(img_data))
                ocr_text = pytesseract.image_to_string(image)
                parsed_text += ocr_text + "\n"
            
            block_counter += 1

    return parsed_text
    
def get_pdf_exam_data(pdf_text: str) -> str:
    version = prompt_llm(
        prompt=PROMPT_CONFIG + f"Extract the exam version from the following text formatted as NXY, where N is the time of year (V for before july, K for august, and H for after september), and XY is the year itself (24 for 2024, 19 for 2019, etc.).:\n\n{pdf_text}",
        is_numeric=False,
        max_len=1000
    )

    subject = prompt_llm(
        prompt=PROMPT_CONFIG + f"Extract the exam subject from the following text. Respond with nothing other than the subject code. Respond with all subject codes in the text separated by a comma (e.g. TMM4100, TMM4102):\n\n{pdf_text}",
        is_numeric=False,
        max_len=1000
    )
    subject_list = [s.strip() for s in subject.split(", ")]

    return version, subject[0]

def write_text_to_file(text: str, exam: str):
    with open(f"{exam}_parsed.txt", "w", encoding="utf-8") as f:
        f.write(text)

def test_classes():
    pdf_path = select_pdf()
    pdf = Pdf(pdf_path)
    # for page in pdf.pages:
    #     print(f"Side {page.page_number} har {len(page.blocks)} blokker")

    #     for block in page.blocks:
    #         print(
    #             f"  Block {block.block_number}: "
    #             f"type={block.type}, top={block.top:.1f}, bottom={block.bottom:.1f}"
    #         )
test_classes()