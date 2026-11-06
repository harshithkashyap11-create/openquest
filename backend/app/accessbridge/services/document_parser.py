"""Parse untrusted documents into ordered, source-traceable text blocks."""

import io
import re
import zipfile
from pathlib import Path
from typing import Literal, cast

from app.accessbridge.domain import SourceBlock, SourceLesson
from fastapi import HTTPException

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _classify(text, heading, previous_heading):
    clean = text.strip()
    lower = clean.lower()
    section = (previous_heading or "").lower()
    if heading:
        return "heading"
    if re.match(
        r"(?:safety|warning|caution)\s*[:—-]|(?:never|do not|don't)\s+(?:taste|touch|drink|eat|mix)",
        lower,
    ):
        return "safety"
    if "diagram" in section or lower.startswith("diagram:"):
        return "diagram"
    if "glossary" in section or "vocabulary" in section:
        return "glossary"
    if "materials" in section:
        return "materials"
    if "assessment" in section or "questions" in section or clean.endswith("?"):
        return "question"
    if re.match(r"\d+[.)]\s", clean):
        return "activity"
    if re.match(r"[-*•]\s", clean):
        return "list"
    return "paragraph"


def _plain_blocks(text):
    """Blank lines separate prose; headings and numbered lines stay addressable."""
    result = []
    for group in re.split(r"\n\s*\n", text):
        lines = group.strip().splitlines()
        if not lines:
            continue
        if any(re.match(r"\s*(?:#{1,6}\s|\d+[.)]\s|[-*•]\s)", line) for line in lines):
            result.extend(
                (line.strip(), bool(re.match(r"^#{1,6}\s", line.strip())))
                for line in lines
                if line.strip()
            )
        else:
            joined = " ".join(line.strip() for line in lines)
            heading = len(joined) < 110 and (
                joined.endswith(":")
                or joined
                in {
                    "Learning Objectives",
                    "Importance of Photosynthesis",
                    "Learning Activity",
                    "Materials",
                    "Instructions",
                    "Diagram Description",
                    "Assessment Questions",
                    "Summary",
                    "Safety",
                    "Vocabulary",
                    "Glossary",
                }
            )
            result.append((joined, heading))
    return result


def parse_document(name, data, max_chars=60000, max_bytes=MAX_UPLOAD_BYTES):
    safe_name = Path(str(name).replace("\\", "/")).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(
            415, "Please upload a PDF, DOCX, UTF-8 TXT or Markdown lesson."
        )
    if len(data) > max_bytes:
        raise HTTPException(413, "The lesson exceeds the 10 MB upload limit.")
    if not data:
        raise HTTPException(
            422, "This file is empty. Please choose a lesson with readable text."
        )
    extracted = []
    warnings = []
    try:
        if suffix == ".pdf":
            import pymupdf
            if not data.lstrip().startswith(b"%PDF-"):
                raise ValueError("The file contents do not match a PDF signature.")
            with pymupdf.open(stream=data, filetype="pdf") as pdf:
                if pdf.needs_pass:
                    raise ValueError("Password-protected PDFs are unsupported.")
                if len(pdf) > 100:
                    raise ValueError("Please use a lesson of 100 pages or fewer.")
                for page_index in range(len(pdf)):
                    page_no, page = page_index + 1, pdf[page_index]
                    # sort=True uses page reading order; arbitrary column layout needs review.
                    for raw in page.get_text("blocks", sort=True):
                        if len(raw) > 6 and raw[6] != 0:
                            continue
                        for text, heading in _plain_blocks(raw[4]):
                            extracted.append((text, heading, page_no))
                warnings.append(
                    "PDF reading order is inferred from text positions; review multi-column layouts and diagram descriptions. Source images are not interpreted."
                )
        elif suffix == ".docx":
            from docx import Document
            from docx.oxml.ns import qn
            from docx.table import Table
            from docx.text.paragraph import Paragraph
            if not data.startswith(b"PK\x03\x04"):
                raise ValueError("The file contents do not match a DOCX ZIP signature.")
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if (
                    sum(item.file_size for item in archive.infolist())
                    > 30 * 1024 * 1024
                ):
                    raise ValueError(
                        "The uncompressed document exceeds the 30 MB limit."
                    )
                if (
                    "word/document.xml" not in archive.namelist()
                    or "[Content_Types].xml" not in archive.namelist()
                ):
                    raise ValueError("This ZIP archive is not a Word DOCX document.")
                if any(item.flag_bits & 1 for item in archive.infolist()):
                    raise ValueError("Encrypted documents are unsupported.")
            doc = Document(io.BytesIO(data))
            for node in doc.element.body.iterchildren():
                if node.tag == qn("w:p"):
                    paragraph = Paragraph(node, doc)
                    if paragraph.text.strip():
                        style_name = (
                            paragraph.style.name if paragraph.style is not None else ""
                        )
                        extracted.append(
                            (
                                paragraph.text.strip(),
                                (style_name or "").startswith(("Heading", "Title")),
                                None,
                            )
                        )
                elif node.tag == qn("w:tbl"):
                    table = Table(node, doc)
                    for row in table.rows:
                        content = " | ".join(cell.text.strip() for cell in row.cells)
                        if content.strip(" |"):
                            extracted.append((content, False, None))
            warnings.append(
                "DOCX images are not interpreted; supplied captions and textual descriptions require teacher review."
            )
        else:
            if data.startswith((b"%PDF-", b"PK\x03\x04", b"\x89PNG", b"\xff\xd8\xff")):
                raise ValueError("The file contents do not match its text extension.")
            text = data.decode("utf-8-sig")
            if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
                raise ValueError("The text file contains binary data. Use UTF-8 text.")
            extracted = [(text, heading, None) for text, heading in _plain_blocks(text)]
    except Exception as exc:  # noqa: BLE001 — normalize third-party parser errors at the upload boundary.
        detail = (
            str(exc)
            if isinstance(exc, (ValueError, UnicodeError))
            else "The document could not be read. It may be corrupted or unsupported."
        )
        raise HTTPException(422, detail) from None
    total = sum(len(text) for text, _, _ in extracted)
    if total < 30:
        raise HTTPException(
            422,
            "No usable lesson text found. Scanned or image-only PDFs require OCR, which is not supported.",
        )
    if total > max_chars:
        raise HTTPException(
            422,
            f"This lesson is too long. Please use fewer than {max_chars:,} characters.",
        )
    blocks = []
    current_heading = None
    for index, (text, heading, page) in enumerate(extracted):
        text = re.sub(r"^#{1,6}\s+", "", text).strip()
        kind = _classify(text, heading, current_heading)
        if heading:
            current_heading = text.rstrip(":")
        blocks.append(
            SourceBlock(
                block_id=f"source-{index + 1:03}",
                block_type=kind,
                text=text,
                order_index=index,
                source_page=page,
                source_heading=current_heading,
            )
        )
    title = blocks[0].text[:240] if blocks else Path(safe_name).stem
    return SourceLesson(
        title=title,
        source_filename=safe_name,
        source_format=cast(Literal["pdf", "docx", "txt", "md"], suffix[1:]),
        blocks=blocks,
        parsing_warnings=warnings,
    )


def extract_document(name, data, max_chars=60000):
    """Compatibility utility; new ingestion persists parse_document's structured data."""
    return "\n\n".join(
        block.text for block in parse_document(name, data, max_chars).blocks
    )
