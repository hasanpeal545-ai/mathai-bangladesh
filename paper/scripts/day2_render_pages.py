"""Day 2 / Task A: render the 5 selected Chapter 2 pages to 300-DPI PNGs for the paper.

Pages (1-based PDF page numbers, i.e. fitz index = N-1):
  Bangla  class_9_General_math_bn.pdf  -> 30, 36, 44
  English class_9_General_math_en.pdf  -> 30, 38

Saves to paper/page_images/{lang}_page_{N}.png and, as a sanity check, prints the
first 2 lines of the matching backend/data/ocr_raw/class_9_General_math_{lang}/page_N.txt
so Peal can visually confirm the rendered image matches the already-extracted OCR text.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BN_PDF = os.path.join(ROOT, "backend", "data", "pdfs", "2026", "bangla", "class_9_General_math_bn.pdf")
EN_PDF = os.path.join(ROOT, "backend", "data", "pdfs", "2026", "english", "class_9_General_math_en.pdf")
OUT_DIR = os.path.join(ROOT, "paper", "page_images")
OCR_RAW_DIR = os.path.join(ROOT, "backend", "data", "ocr_raw", "class_9_General_math_{lang}")

DPI = 300
TARGETS = [
    ("bn", BN_PDF, [30, 36, 44]),
    ("en", EN_PDF, [30, 38]),
]


def render_page(pdf_path, page_number_1based, out_path, dpi=DPI):
    doc = fitz.open(pdf_path)
    page = doc[page_number_1based - 1]  # fitz index = N-1
    zoom = dpi / 72.0  # PyMuPDF's base unit is 72 DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(out_path)
    doc.close()
    return pix.width, pix.height


def print_sanity_check(lang, page_number):
    ocr_path = os.path.join(OCR_RAW_DIR.format(lang=lang), f"page_{page_number}.txt")
    print(f"  Sanity check -> {os.path.relpath(ocr_path, ROOT)}")
    if not os.path.exists(ocr_path):
        print("    [MISSING] OCR raw file not found.")
        return
    with open(ocr_path, encoding="utf-8") as fh:
        lines = [fh.readline().rstrip("\n") for _ in range(2)]
    for i, line in enumerate(lines, 1):
        print(f"    line {i}: {line}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for lang, pdf_path, pages in TARGETS:
        if not os.path.exists(pdf_path):
            print(f"[MISSING] source PDF not found: {pdf_path}")
            continue
        for n in pages:
            out_path = os.path.join(OUT_DIR, f"{lang}_page_{n}.png")
            w, h = render_page(pdf_path, n, out_path, dpi=DPI)
            print(f"Rendered {lang} page {n} -> {os.path.relpath(out_path, ROOT)} ({w}x{h}px @ {DPI} DPI)")
            print_sanity_check(lang, n)
            print()


if __name__ == "__main__":
    main()
