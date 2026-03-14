import io
import os
import tempfile
from pathlib import Path
from this import d

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

from app.models.common_types import DocumentType


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, int]:
    """Extract text from PDF. Returns (text, page_count)."""
    import pdfplumber

    text_parts = []
    page_count = 0

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            # Try native text extraction first
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text_parts.append(page_text)
            else:
                # Scanned page — fall back to OCR
                page_text = _ocr_pdf_page(page)
                if page_text:
                    text_parts.append(page_text)

            # Also extract tables (preserves lab report structure)
            tables = page.extract_tables()
            for table in tables:
                table_text = _format_table(table)
                if table_text:
                    text_parts.append(table_text)

    return "\n\n".join(text_parts), page_count


def _ocr_pdf_page(page) -> str:
    """OCR a single pdfplumber page object."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        from PIL import Image

        # Render page to image
        img = page.to_image(resolution=300).original
        return pytesseract.image_to_string(img, lang="eng")
    except Exception:
        return ""


def extract_text_from_image(file_bytes: bytes, document_type: DocumentType) -> str:
    """Extract text from an image using OCR."""
    if document_type == DocumentType.LAB_REPORTS:
        return extract_text_from_image_lab_report(file_bytes)
    else:
        return extract_text_from_prescription(file_bytes)


def extract_text_from_image_lab_report(file_bytes: bytes) -> str:
    """Extract text from an image using OCR."""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang="eng")
    except Exception as e:
        return f"[OCR failed: {e}]"


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a .docx file."""
    try:
        import docx

        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        return f"[DOCX extraction failed: {e}]"


def extract_text(
    file_bytes: bytes, mime_type: str, document_type: DocumentType
) -> tuple[str, int]:
    """
    Route to the correct extractor based on MIME type.
    Returns (text, page_count).
    """
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)
    elif mime_type in ("image/png", "image/jpeg", "image/jpg"):
        return extract_text_from_image(file_bytes, document_type), 1
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return extract_text_from_docx(file_bytes), 1
    elif mime_type == "text/plain":
        return file_bytes.decode("utf-8", errors="replace"), 1
    else:
        return "[Unsupported file type]", 0


def extract_text_from_prescription(file_bytes: bytes) -> str:

    processor = DonutProcessor.from_pretrained("chinmays18/medical-prescription-ocr")
    model = VisionEncoderDecoderModel.from_pretrained(
        "chinmays18/medical-prescription-ocr"
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    img = Image.open(io.BytesIO(file_bytes))
    pixel_values = processor(images=img, return_tensors="pt").pixel_values.to(device)
    task_prompt = "<s_ocr>"
    decoder_input_ids = processor.tokenizer(
        task_prompt, return_tensors="pt"
    ).input_ids.to(device)

    generated_ids = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=512,
        num_beams=1,
        early_stopping=True,
    )

    # Decode the generated text
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(generated_text)
    return ""


def _format_table(table: list[list]) -> str:
    """Format a pdfplumber table as pipe-separated rows."""
    if not table:
        return ""
    rows = []
    for row in table:
        cleaned = [str(cell or "").strip() for cell in row]
        rows.append(" | ".join(cleaned))
    return "\n".join(rows)


def detect_doc_type(filename: str, text_sample: str) -> str:
    """Heuristically detect document type from filename and content."""
    fname = filename.lower()
    sample = text_sample.lower()[:500]

    if any(kw in fname for kw in ["lab", "blood", "report", "test", "result"]):
        return "lab_report"
    if any(kw in fname for kw in ["prescription", "rx", "medicine", "medic"]):
        return "prescription"
    if any(
        kw in fname
        for kw in ["xray", "x-ray", "mri", "ct", "scan", "imaging", "radiol"]
    ):
        return "imaging"

    if any(
        kw in sample
        for kw in [
            "hemoglobin",
            "hba1c",
            "glucose",
            "cholesterol",
            "creatinine",
            "wbc",
            "rbc",
            "platelet",
        ]
    ):
        return "lab_report"
    if any(
        kw in sample
        for kw in ["prescribed", "tablet", "capsule", "mg ", "dosage", "dose", "refill"]
    ):
        return "prescription"
    if any(
        kw in sample for kw in ["impression", "findings", "radiolog", "mri", "ct scan"]
    ):
        return "imaging"

    return "other"
