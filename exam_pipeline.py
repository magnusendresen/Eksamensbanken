from __future__ import annotations
import code
import os
import time
import threading
import tkinter as tk
from tkinter import filedialog
from openai import OpenAI
import fitz
from typing import Literal
import pytesseract
from PIL import Image
from io import BytesIO
import json
import random
from typing import Literal

from prompt_llm import prompt_llm
from ocr import ocr_image, page_to_img_bytes, run_in_threads
import db
from my_dicts import MAIN_CATEGORIES


PASSWORD = os.getenv("psql_psw")
assert PASSWORD is not None, "psql_psw env var not set"
DATABASE_URL = f"postgresql://postgres:{PASSWORD}@localhost:5432/eksamensbanken"
mydb = db.DB(DATABASE_URL)
SUBJECTS_PATH = "ntnu_emner.json"  # juster én gang

def sample_subject_field(
    field: Literal["Emnekode", "Emnenavn", "Sted", "Temaer"],
    n: int
) -> str:
    with open(SUBJECTS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    n = min(n, len(data))
    indices = random.sample(range(len(data)), n)

    values = []
    for i in indices:
        value = data[i].get(field)
        if value is None:
            continue
        if isinstance(value, list):
            continue  # vi vil ikke ha lister i prompt-eksempler
        values.append(str(value))

    return ", ".join(values)


class Subject:
    id: int
    code: str
    name: str
    category: Topic
    lang: str


    def __init__(self, raw_text):
        self.code = self.extract_subject_code(raw_text)
        self.name = self.extract_subject_name(raw_text)
        self.category = Topic(self.identify_category_and_type(raw_text))

        if self.category.type == "main":
            # make sure that core topics and possible sub topics are used
            pass
        elif self.cateogry.type == "core":
            # make sure that the sub topics of the core topic is used
            pass

        if self.category:
            print(f"Topic extraction successful with value: {self.topic.name}!")
        mydb.add_entity(self) # Assigns self.id

    def identify_category_and_type(self, raw_text) -> str:
        category = prompt_llm(
            system_prompt=(
                "Identify the main academic category of the subject from the following text. "
                "Respond with nothing other than the single category name. The possible "
                f"categories are: {arr_to_enum_str(MAIN_CATEGORIES)}"
            ),
            user_prompt=raw_text,
            response_type="text",
            max_len=100
        )
        sufficient = prompt_llm(
            system_prompt=(
                f"Determine if the category {category} is sufficient to define this exams "
                "academic field or if a more specific topic is needed. Respond with " # Some amazing prompt needed.
                "either 0 or 1, where 0: no, 1: yes. "
            ),
            user_prompt=(raw_text),
            response_type="number",
            max_len=2
        )
        if sufficient == 0:
            topic_type = "core"
            category = prompt_llm(
                system_prompt=(
                    "" # Some amazing prompt to extract core topics from the following text. 
                ),
                user_prompt=raw_text,
                response_type="text",
                max_len=50
            )
        else:
            topic_type = "main"


        return category, topic_type


    def extract_subject_code(self, raw_text) -> str:
        return prompt_llm(
            system_prompt=(
                "Extract the exam subject code from the following text. Respond with "
                "nothing other than the subject codes. Respond with all subject "
                "codes in the text separated by a comma. "
                f"E.g.: {sample_subject_field('Emnekode', 50)}"
            ),
            user_prompt=raw_text,
            response_type="text_list",
            max_len=200
        )
    
    def extract_subject_name(self, raw_text) -> str:
        return prompt_llm(
            system_prompt=(
                "Extract the exam subject name from the following text. Respond with "
                "nothing other than the subject name. Respond with the full subject name. "
                f"E.g.: {sample_subject_field('Emnenavn', 50)}"
            ),
            user_prompt=raw_text,
            response_type="text_list",
            max_len=200
        )

class Topic:
    id: int
    name: str
    type: Literal["core", "sub", "category"] # May be renamed later

    def __init__(self, raw_text, type):
        self.type = type
        self.name = self.extract_topic(raw_text, type)

        mydb.add_entity(self) # Assigns self.id

"""    def extract_topic(self, raw_text, depth) -> str:
        topic_id = prompt_llm(
            system_prompt=(
                "Extract the number of the topic assiciated with the following text. "
                "Respond with nothing other than the single number."
                f"The topics to be chosen form are: {arr_to_enum_str(MAIN_CATEGORIES)} "
            ),
            user_prompt=raw_text,
            response_type="number",
            max_len=50
        )
        return MAIN_CATEGORIES[int(topic_id)-1]"""
    

class Exam: # Should generally be named assessment in the future, as it may include assignments etc.
    id: int
    subject: Subject
    assessment_type: str # e.g. Exam, assignment, home exam, etc. (coursework?)
    year: int

    def __init__(self, pdf_path):
        self.version = ""

        mydb.add_entity(self) # Assigns self.id

        Pdf(self, pdf_path)

        raw_text = self.collect_raw_text()
        self.version = self.extract_version(raw_text)

        self.subject = Subject(raw_text=raw_text)
        
        mydb.set_values(self, ["subject"])
        mydb.set_values(self, ["version"])

        print(f"Exam created with id={self.id}, version={self.version}, subject={self.subject.name}")

    def collect_raw_text(self) -> str:
        raw_text = ""
        for pdf in mydb.select_children(parent_cls=Exam, child_cls=Pdf, parent_id=self.id):
            for page in mydb.select_children(parent_cls=Pdf, child_cls=Page, parent_id=pdf["id"], order_by=["page_number"]):
                for block in mydb.select_children(parent_cls=Page, child_cls=PdfBlock, parent_id=page["id"], order_by=["block_number"]):
                    raw_text += block["raw_text"]
        return raw_text
    
    def extract_version(self, raw_text) -> str:
        return prompt_llm(
            system_prompt=(
                "Extract the exam version from the following text formatted as NXY, "
                "where N is the time of year (V for before july, K for august, and H "
                "for after september), and XY is the year itself (24 for 2024, 19 for "
                "2019, etc.)."
            ),
            user_prompt=raw_text,
            max_len=10
        )

class Task:
    id: int
    exam: Exam
    task_number: str
    raw_text: str
    task_text: str
    code_text: str
    images: list[str]
    solution_text: str
    points: float
    raw_text: str
    topic: str
    bbox: list[float]
    topic: Topic

    def __init__(self, exam, task_number):
        self.exam = exam
        self.task_number = task_number

        mydb.add_entity(self) # Assigns self.id
            
        
    def collect_raw_text(self) -> str:
        raw_text = ""
        for pdf in mydb.select_children(parent_cls=Exam, child_cls=Pdf, parent_id=self.id):
            for page in mydb.select_children(parent_cls=Pdf, child_cls=Page, parent_id=pdf["id"], order_by=["page_number"]):
                for block in mydb.select_children(parent_cls=Page, child_cls=PdfBlock, parent_id=page["id"], order_by=["block_number"]):
                    raw_text += block["raw_text"]
        return raw_text
    

class Pdf:
    id: int
    exam: Exam
    name: str
    path: str
    
    def __init__(self, exam, path):
        self.exam = exam
        self.name = ""

        self.raw_pdf = fitz.open(path)
        self.path = path

        mydb.add_entity(self) # Assigns self.id

        for i, raw_page in enumerate(self.raw_pdf):
            Page(pdf=self, raw_page=raw_page, page_number=i)


        """
        self.name = f"{self.exam.subject.code}_{self.exam.version}"

        os.rename(self.path, f"{self.name}.pdf")
        self.path = f"{self.name}.pdf"
        """


class Page:
    id: int
    pdf: Pdf
    page_number: int
    ocr_text: str

    def __init__(self, pdf, raw_page, page_number: int):
        self.pdf = pdf
        self.raw_page = raw_page
        
        self.page_number = page_number

        self.ocr_text = str(ocr_image(page_to_img_bytes(raw_page)))

        mydb.add_entity(self) # Assigns self.id

        for i, raw_block in enumerate(raw_page.get_text("dict")["blocks"]):
            PdfBlock(page=self, raw_block=raw_block, block_number=i)


class PdfBlock:
    id: int
    page: Page
    block_number: int
    type: int # 0=Text, 1=Image
    raw_text: str
    bbox: list[float]

    def __init__(self, page, raw_block, block_number: int):
        self.page = page

        self.raw_block = raw_block

        self.block_number = block_number
        self.type = raw_block["type"]

        self.raw_text = self.get_block_text()

        self.bbox = raw_block["bbox"]

        mydb.add_entity(self)
        print(f"PdfBlock.id = {self.id}, page.page_number = {self.page.page_number}, pdf.id = {self.page.pdf.id}")

    
    def get_block_text(self) -> str:
        block_text = ""
        if self.type == 0:
            for line in self.raw_block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "") + "\n"
        elif self.type == 1: # Image
            x0, y0, x1, y1 = self.raw_block["bbox"]
            pix = self.page.raw_page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1))
            img_data = pix.tobytes("png")
            image = Image.open(BytesIO(img_data))
            block_text = pytesseract.image_to_string(image)
        else:
            block_text = ""
        return block_text

def select_pdf() -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    file_path = filedialog.askopenfilename(
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf")],
        parent=root
    )
    root.destroy()
    return file_path

def write_text_to_file(text: str, exam: str) -> None:
    with open(f"{exam}_parsed.txt", "w", encoding="utf-8") as f:
        f.write(text)

def test_classes() -> None:
    pdf_path = select_pdf()
    Exam(pdf_path)


def arr_to_enum_str(arr: list[str]) -> str:
    for i, item in enumerate(arr):
        arr[i] = f"{i+1}: {item}"
    return "\n".join(arr)  

def reset_database():
    mydb.delete_tables()
    for cls in [Subject, Exam, Task, Pdf, Page, PdfBlock, Topic]:
        mydb.create_table(cls)

    mydb.create_relation_table(Topic)

    mydb.metadata.create_all(mydb.engine)

if __name__ == "__main__":
    reset_database()
    test_classes()