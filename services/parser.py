import io
import re
from fastapi import UploadFile, HTTPException


async def extract_text(file: UploadFile) -> str:
    """
    Extract plain text from an uploaded PDF or DOCX file.
    Returns the raw text string.
    """
    content = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        return _parse_pdf(content)
    elif filename.endswith(".docx"):
        return _parse_docx(content)
    elif filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Upload PDF, DOCX, or TXT.")


def _parse_pdf(content: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {str(e)}")


def _parse_docx(content: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse DOCX: {str(e)}")


def extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else None


def extract_name(text: str) -> str | None:
    """Heuristic: first non-empty line is usually the candidate's name."""
    for line in text.splitlines():
        clean = line.strip()
        if clean and len(clean.split()) <= 5 and not "@" in clean:
            return clean
    return None


def truncate(text: str, max_chars: int = 4000) -> str:
    return text[:max_chars] + ("..." if len(text) > max_chars else "")
