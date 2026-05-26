from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from src.pdf_app.utils.page_spec import parse_page_sequence, parse_page_spec


def _open_reader(pdf_path: str, password: str | None = None) -> PdfReader:
    reader = PdfReader(pdf_path)
    if not reader.is_encrypted:
        return reader

    password_to_try = "" if password is None else password
    try:
        decrypted = reader.decrypt(password_to_try)
    except Exception as exc:
        msg = str(exc)
        if "cryptography" in msg and "AES" in msg:
            raise RuntimeError(
                "This PDF uses AES encryption and requires the 'cryptography' package."
            ) from exc
        raise

    if not decrypted:
        raise PermissionError("This PDF is encrypted and requires a valid password.")

    return reader


def inspect_pdf(pdf_path: str, password: str | None = None) -> dict:
    reader = _open_reader(pdf_path, password=password)
    metadata = reader.metadata or {}
    return {
        "path": str(Path(pdf_path).resolve()),
        "pages": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "metadata": {str(k): str(v) for k, v in metadata.items()},
    }


def render_page_preview(
    pdf_path: str,
    page_number_1_based: int,
    zoom: float = 1.2,
    password: str | None = None,
) -> bytes:
    """
    Render a PDF page to PNG bytes preserving visual layout (fonts, images, style).
    """
    if zoom <= 0:
        raise ValueError("Zoom must be greater than 0.")

    try:
        import pymupdf as fitz  # type: ignore
    except Exception as exc:
        raise RuntimeError("Visual preview requires the 'pymupdf' package.") from exc

    doc = fitz.open(pdf_path)
    try:
        if doc.needs_pass:
            password_to_try = "" if password is None else password
            if not doc.authenticate(password_to_try):
                raise PermissionError("This PDF is encrypted and requires a valid password.")

        total_pages = doc.page_count
        if page_number_1_based < 1 or page_number_1_based > total_pages:
            raise ValueError(f"Page {page_number_1_based} is out of bounds (1-{total_pages}).")

        page = doc.load_page(page_number_1_based - 1)
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")
    finally:
        doc.close()


def read_page_text(pdf_path: str, page_number_1_based: int, password: str | None = None) -> str:
    reader = _open_reader(pdf_path, password=password)
    total_pages = len(reader.pages)
    if page_number_1_based < 1 or page_number_1_based > total_pages:
        raise ValueError(f"Page {page_number_1_based} is out of bounds (1-{total_pages}).")

    text = reader.pages[page_number_1_based - 1].extract_text() or ""
    if not text.strip():
        return "[No extractable text on this page.]"
    return text


def merge_pdfs(input_paths: list[str], output_path: str, password: str | None = None) -> None:
    if not input_paths:
        raise ValueError("No input PDFs selected for merge.")

    writer = PdfWriter()
    for path in input_paths:
        reader = _open_reader(path, password=password)
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, "wb") as out_file:
        writer.write(out_file)


def _resolve_merge_page_indexes(page_spec: str, total_pages: int) -> list[int]:
    cleaned = page_spec.strip().lower()
    if cleaned in {"", "all", "*"}:
        return list(range(total_pages))
    return parse_page_sequence(page_spec, total_pages)


def merge_pdf_segments(
    segments: list[dict[str, str]], output_path: str, password: str | None = None
) -> None:
    """
    Merge ordered segments where each segment is:
    {"path": "...", "page_spec": "all" | "1,3-5,2"}
    """
    if not segments:
        raise ValueError("No merge segments provided.")

    writer = PdfWriter()
    total_output_pages = 0

    for segment in segments:
        path = segment.get("path", "").strip()
        if not path:
            raise ValueError("A merge segment is missing a PDF path.")

        page_spec = segment.get("page_spec", "all")
        reader = _open_reader(path, password=password)
        total_pages = len(reader.pages)
        try:
            indexes = _resolve_merge_page_indexes(page_spec, total_pages)
        except ValueError as exc:
            raise ValueError(f"{Path(path).name}: {exc}") from exc

        for idx in indexes:
            writer.add_page(reader.pages[idx])
            total_output_pages += 1

    if total_output_pages == 0:
        raise ValueError("No pages selected to merge.")

    with open(output_path, "wb") as out_file:
        writer.write(out_file)


def rotate_pages(
    input_path: str,
    output_path: str,
    page_spec: str,
    angle: int,
    password: str | None = None,
) -> None:
    if angle not in {90, 180, 270}:
        raise ValueError("Angle must be one of: 90, 180, 270.")

    reader = _open_reader(input_path, password=password)
    total_pages = len(reader.pages)
    selected = parse_page_spec(page_spec, total_pages)

    writer = PdfWriter()
    for idx, page in enumerate(reader.pages):
        if idx in selected:
            page.rotate(angle)
        writer.add_page(page)

    with open(output_path, "wb") as out_file:
        writer.write(out_file)


def remove_pages(
    input_path: str, output_path: str, page_spec: str, password: str | None = None
) -> None:
    reader = _open_reader(input_path, password=password)
    total_pages = len(reader.pages)
    to_remove = parse_page_spec(page_spec, total_pages)

    if len(to_remove) >= total_pages:
        raise ValueError("Cannot remove all pages from the document.")

    writer = PdfWriter()
    for idx, page in enumerate(reader.pages):
        if idx not in to_remove:
            writer.add_page(page)

    with open(output_path, "wb") as out_file:
        writer.write(out_file)


def extract_pages(
    input_path: str, output_path: str, page_spec: str, password: str | None = None
) -> None:
    reader = _open_reader(input_path, password=password)
    total_pages = len(reader.pages)
    selected = sorted(parse_page_spec(page_spec, total_pages))

    writer = PdfWriter()
    for idx in selected:
        writer.add_page(reader.pages[idx])

    with open(output_path, "wb") as out_file:
        writer.write(out_file)
