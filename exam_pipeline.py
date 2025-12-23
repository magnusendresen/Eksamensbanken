from __future__ import annotations
import os
import time
import tkinter as tk
from tkinter import filedialog
from openai import OpenAI
import fitz
from typing import Literal
import pytesseract
from PIL import Image
from io import BytesIO
from prompt_llm import prompt_llm
from ocr import ocr_image, page_to_img_bytes, run_in_threads

class Subject:
    code: str
    name: str
    category: str
    topics: list[str]

    def __init__(self, code):
        self.code = code


class Exam:
    pdf: str
    solution_pdf: object
    subject: str
    tasks: list[str]
    solutions: list[str]

    def __init__(self, pdf_path):
        #self.name = f"{subject.code.strip().upper()}_{version.strip().upper()}"
        self.pdf = Pdf(path=pdf_path)

    def assign_subject(self):
        return prompt_llm(
            system_prompt=(
                "Extract the exam subject from the following text. Respond with "
                "nothing other than the subject codes. Respond with all subject "
                "codes in the text separated by a comma (e.g. TMM4100, TMM4102, VB1004)."
            ),
            user_prompt=self.pdf.ocr_text, # Should be raw text not ocr text
            response_type="text_list",
            max_len=200
        )
    def assign_version(self):
        return prompt_llm(
            system_prompt=(
                "Extract the exam version from the following text formatted as NXY, "
                "where N is the time of year (V for before july, K for august, and H "
                "for after september), and XY is the year itself (24 for 2024, 19 for "
                "2019, etc.)."
            ),
            user_prompt=self.pdf.ocr_text, # Should be raw text not ocr text
            max_len=10
        )
        

class Task:
    exam: Exam
    task_number: str
    task_text: str
    code_text: str
    images: list[str]
    solution_text: str
    points: float
    raw_text: str
    topic: str
    bbox: list[float]

    def __init__(self, exam, task_number):
        self.exam = exam
        self.task_number = task_number


class Pdf:
    exam: Exam
    raw_pdf: fitz.Document
    path: str
    pages: list[Page]
    
    def __init__(self, path: str):
        self.raw_pdf = fitz.open(path)
        self.path = path

        for i, raw_page in enumerate(self.raw_pdf):
            self.pages.append(Page(pdf=self, raw_page=raw_page, page_number=i))

class Page:
    pdf: Pdf
    raw_page: fitz.Page
    page_number: int
    ocr_text: str
    blocks: list[PdfBlock]

    def __init__(self, pdf, raw_page, page_number: int):
        self.pdf = pdf
        self.raw_page = raw_page
        self.page_number = page_number

        self.ocr_text = ocr_image(page_to_img_bytes(raw_page))

        for i, raw_block in enumerate(raw_page.get_text("dict")["blocks"]):
            self.blocks.append(PdfBlock(page=self, raw_block=raw_block, block_number=i))

class PdfBlock:
    page: Page
    raw_block: dict[str, any]
    block_number: int
    type: Literal[0,1]
    raw_text: str
    bbox: list[float]

    def __init__(self, page, raw_block, block_number: int):
        self.page = page
        self.raw_block = raw_block

        self.block_number = block_number
        self.type = raw_block["type"]

        self.raw_text = self.get_block_text()

        self.bbox = raw_block["bbox"]
    
    def get_block_text(self):
        block_text = ""
        if self.type == 0:
            for line in self.raw_block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "") + "\n"
        elif self.type == 1: # Image
            x0, y0, x1, y1 = self.raw_block["bbox"]
            pix = self.page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1))
            img_data = pix.tobytes("png")
            image = Image.open(BytesIO(img_data))
            block_text = pytesseract.image_to_string(image)
        else:
            block_text = ""
        return block_text

def select_pdf():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf")]
    )
    return file_path

def write_text_to_file(text: str, exam: str):
    with open(f"{exam}_parsed.txt", "w", encoding="utf-8") as f:
        f.write(text)

def test_classes():
    pdf_path = select_pdf()
    pdf = Pdf(pdf_path)
    # for page in pdf.pages:
    #     print(f"Side {page.page_number} har {len(page.blocks)} blokker")
    #
    #     for block in page.blocks:
    #         print(
    #             f"  Block {block.block_number}: "
    #             f"type={block.type}, top={block.top:.1f}, bottom={block.bottom:.1f}"
    #         )

# test_classes()
