import os
import io
import csv
import json
import base64
from typing import Optional


ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".doc", ".docx",
    ".csv", ".json", ".py", ".js",
    ".pdf", ".jpg", ".jpeg", ".png", ".webp",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# Text-based file extensions (content can be extracted as text)
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".doc", ".docx", ".pdf"}
# Image file extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_file(filename: str, file_size: int) -> Optional[str]:
    """Validate file format and size. Returns error message or None."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"不支持的文件格式: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if file_size > MAX_FILE_SIZE:
        return f"文件过大: {file_size / 1024 / 1024:.1f}MB，限制 20MB"
    return None


def is_text_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in TEXT_EXTENSIONS


def is_image_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in IMAGE_EXTENSIONS


def parse_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")


def parse_md(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")


def parse_csv(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    # Limit to first 100 rows to avoid huge context
    if len(rows) > 100:
        header = rows[0]
        data_rows = rows[1:100]
        lines = [", ".join(header)]
        for row in data_rows:
            lines.append(", ".join(row))
        lines.append(f"... (共 {len(rows) - 1} 行，仅显示前 100 行)")
        return "\n".join(lines)
    return text


def parse_json_file(content: bytes) -> str:
    text = content.decode("utf-8", errors="ignore")
    try:
        data = json.loads(text)
        formatted = json.dumps(data, ensure_ascii=False, indent=2)
        # Truncate if too long
        if len(formatted) > 50000:
            formatted = formatted[:50000] + "\n... (内容过长，已截断)"
        return formatted
    except json.JSONDecodeError:
        return text


def parse_code(content: bytes) -> str:
    """Parse .py, .js and other code files as plain text."""
    return content.decode("utf-8", errors="ignore")


def parse_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_pdf(content: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append(f"--- 第 {i + 1} 页 ---\n{text.strip()}")
        if not pages:
            return "(PDF 无法提取文字内容)"
        result = "\n\n".join(pages)
        if len(result) > 80000:
            result = result[:80000] + "\n... (内容过长，已截断)"
        return result
    except ImportError:
        return "(PDF 解析需要安装 PyPDF2: pip install PyPDF2)"
    except Exception as e:
        return f"(PDF 解析失败: {str(e)})"


def parse_document(filename: str, content: bytes) -> str:
    """Parse document based on file extension. Returns extracted text."""
    ext = os.path.splitext(filename)[1].lower()

    if ext in (".txt",):
        return parse_txt(content)
    elif ext in (".md",):
        return parse_md(content)
    elif ext in (".csv",):
        return parse_csv(content)
    elif ext in (".json",):
        return parse_json_file(content)
    elif ext in (".py", ".js"):
        return parse_code(content)
    elif ext in (".doc", ".docx"):
        return parse_docx(content)
    elif ext in (".pdf",):
        return parse_pdf(content)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def image_to_base64(filename: str, content: bytes) -> str:
    """Convert image file to base64 data URL for multimodal LLM."""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/jpeg")
    b64 = base64.b64encode(content).decode("utf-8")
    return f"data:{mime};base64,{b64}"
