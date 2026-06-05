import tempfile
import os
from io import BytesIO

from pdf2docx import Converter as PdfToDocxConverter
from docx import Document
from fpdf import FPDF


MAX_FILE_SIZE = 45 * 1024 * 1024


async def pdf_to_word(pdf_bytes: bytes) -> bytes | None:
    if len(pdf_bytes) > MAX_FILE_SIZE:
        return None

    def convert():
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            docx_path = os.path.join(tmpdir, "output.docx")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            cv = PdfToDocxConverter(pdf_path)
            cv.convert(docx_path)
            cv.close()
            with open(docx_path, "rb") as f:
                return f.read()

    loop = __import__("asyncio").get_event_loop()
    return await loop.run_in_executor(None, convert)


async def word_to_pdf(docx_bytes: bytes) -> bytes | None:
    if len(docx_bytes) > MAX_FILE_SIZE:
        return None

    def convert():
        doc = Document(BytesIO(docx_bytes))
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        for para in doc.paragraphs:
            style = para.style.name.lower()
            text = para.text.strip()
            if not text:
                continue
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)

            if "heading" in style:
                level = style.replace("heading", "").strip()
                if level and level.isdigit():
                    size = max(14, 20 - int(level) * 2)
                    pdf.set_font("Helvetica", style="B", size=size)
                else:
                    pdf.set_font("Helvetica", style="B", size=16)
            pdf.multi_cell(0, 10, text)

        return pdf.output(dest="S").encode("latin-1", errors="replace")

    loop = __import__("asyncio").get_event_loop()
    return await loop.run_in_executor(None, convert)
