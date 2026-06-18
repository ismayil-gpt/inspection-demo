import base64
import io
from pathlib import Path
import fitz  # PyMuPDF


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[dict]:
    """Convert PDF bytes to list of base64-encoded page images."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("jpeg")
        encoded = base64.standard_b64encode(img_bytes).decode("utf-8")
        pages.append({
            'page_number': page_num + 1,
            'base64': encoded,
            'width': pix.width,
            'height': pix.height,
        })
    doc.close()
    return pages


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")
