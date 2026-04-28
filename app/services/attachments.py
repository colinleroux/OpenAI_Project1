from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".html", ".css", ".js"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}


@dataclass(frozen=True)
class RequestAttachment:
    filename: str
    path: Path
    kind: str
    extracted_text: str = ""


def save_request_attachments(files: list[FileStorage], upload_dir: str) -> list[RequestAttachment]:
    target_dir = Path(upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    attachments = []
    for file in files:
        if not file or not file.filename:
            continue

        filename = secure_filename(file.filename)
        if not filename:
            continue

        path = _unique_path(target_dir / filename)
        file.save(path)
        kind = _classify(path)
        attachments.append(
            RequestAttachment(
                filename=path.name,
                path=path,
                kind=kind,
                extracted_text=_extract_text(path, kind),
            )
        )

    return attachments


def load_saved_attachments(paths: list[str], upload_dir: str) -> list[RequestAttachment]:
    upload_root = Path(upload_dir).resolve()
    attachments = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        if not path.exists() or not path.is_file():
            continue
        if upload_root not in path.parents and path.parent != upload_root:
            continue

        kind = _classify(path)
        attachments.append(
            RequestAttachment(
                filename=path.name,
                path=path,
                kind=kind,
                extracted_text=_extract_text(path, kind),
            )
        )
    return attachments


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return "text"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    if suffix in DOCX_EXTENSIONS:
        return "docx"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return "unsupported"


def _extract_text(path: Path, kind: str) -> str:
    if kind == "text":
        return path.read_text(encoding="utf-8", errors="replace")
    if kind == "docx":
        return _extract_docx_text(path)
    return ""


def _extract_docx_text(path: Path) -> str:
    try:
        with ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except (BadZipFile, KeyError):
        return ""

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(xml_bytes)
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)
