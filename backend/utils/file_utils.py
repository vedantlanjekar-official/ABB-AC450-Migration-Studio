import re
import shutil
from pathlib import Path
from typing import Optional, Sequence, Union
from backend.core.config import settings


def cleanup_job_files(job_id: str) -> None:
    """Cleans up temporary upload directory and files for a job."""
    upload_dir = settings.UPLOAD_DIR / job_id
    if upload_dir.exists():
        try:
            shutil.rmtree(upload_dir)
        except Exception:
            pass


def sanitize_filename(filename: str) -> str:
    """
    Keep the original basename for upload storage.

    Preserves spaces, underscores, hyphens, and capitalization.
    Only strips path components and null / separator characters.
    """
    name = Path(filename or "").name
    name = name.replace("\x00", "").replace("/", "_").replace("\\", "_")
    return name.strip() or "upload.bin"


def pdf_to_excel_filename(pdf_filename: str) -> str:
    """
    Derive Excel export name from a PDF filename.

    Removes only a trailing .pdf/.PDF extension; everything else is preserved.
    """
    name = Path(pdf_filename or "").name.strip() or "export.pdf"
    if name.lower().endswith(".pdf"):
        return name[:-4] + ".xlsx"
    return f"{Path(name).stem}.xlsx"


def excel_filename_from_uploads(
    uploaded_files: Optional[Sequence[str]],
    *,
    fallback: str = "export.xlsx",
) -> str:
    """
    Pick the Excel download/export filename from uploaded sources.

    Uses the first PDF when present (single-file jobs and multi-PDF DB merges).
    Falls back to a generic name when no PDF is in the upload list.
    """
    files = list(uploaded_files or [])
    for fname in files:
        if str(fname).lower().endswith(".pdf"):
            return pdf_to_excel_filename(str(fname))
    if files:
        stem = Path(str(files[0])).stem
        return f"{stem}.xlsx" if stem else fallback
    return fallback


def unique_output_path(directory: Union[str, Path], filename: str) -> Path:
    """
    Return directory/filename, adding ' (2)', ' (3)', … only on name conflicts.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name or "export.xlsx"
    candidate = directory / safe_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix or ".xlsx"
    match = re.match(r"^(.*?)(?: \((\d+)\))?$", stem)
    base = match.group(1) if match else stem
    start = int(match.group(2)) + 1 if match and match.group(2) else 2
    n = start
    while True:
        alt = directory / f"{base} ({n}){suffix}"
        if not alt.exists():
            return alt
        n += 1
