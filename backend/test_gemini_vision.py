# One-off test: Gemini Vision vs Tesseract OCR on page 15 of the (now correctly
# swapped) Bangla class_6_math_bn.pdf.
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import fitz
import pytesseract
from PIL import Image
import google.generativeai as genai

from config import settings

BACKEND_DIR = Path(__file__).resolve().parent
TESSDATA_DIR = BACKEND_DIR / "data" / "tessdata"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Extract page 15 (index 14) as an image, 2x zoom
doc = fitz.open("data/pdfs/2026/bangla/class_6_math_bn.pdf")
page = doc[14]  # page 15
mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
image_path = "data/test_page.png"
pix.save(image_path)

# 1. Tesseract
tess_config = f"--tessdata-dir {TESSDATA_DIR} --psm 3"
tesseract_text = pytesseract.image_to_string(Image.open(image_path), lang="ben", config=tess_config)

# 2. Gemini Vision
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

gemini_prompt = (
    "এটি বাংলাদেশের NCTB গণিত পাঠ্যবইয়ের একটি পৃষ্ঠা।\n"
    "এই পৃষ্ঠার সম্পূর্ণ টেক্সট হুবহু বের করো।\n"
    "নিচের নিয়ম মানো:\n"
    "- বাংলা সংখ্যা হুবহু রাখো: ১ ২ ৩ ৪ ৫ ৬ ৭ ৮ ৯ ০\n"
    "- ভগ্নাংশ সঠিক রাখো: ১/২, ৩/৪\n"
    "- গণিত চিহ্ন সঠিক রাখো: × ÷ = > < ≥ ≤\n"
    "- কোনো markdown, table, বা formatting করবে না\n"
    "- শুধু plain text দাও"
)

image = Image.open(image_path)
gemini_response = model.generate_content([gemini_prompt, image])
gemini_text = gemini_response.text

print("=== TESSERACT OUTPUT ===")
print(tesseract_text)
print()
print("=== GEMINI VISION OUTPUT ===")
print(gemini_text)
