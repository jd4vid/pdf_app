# PDF Desktop App (Python)

Desktop application to **read**, **edit**, and **combine** PDF files using Python libraries with a graphical interface.

## Features (MVP)

- Read PDF metadata
- Visual PDF page preview (keeps layout, fonts, images, styles)
- Extract page text preview
- Merge selected pages from multiple PDFs with custom segment order
- Edit PDF pages:
  - Rotate selected pages
  - Remove selected pages
  - Extract selected pages into a new PDF
- Optional password input for encrypted PDFs

## Tech Stack

- GUI: `tkinter` (built-in with Python on most installs)
- Visual rendering: `pymupdf` + `pillow`
- PDF processing/editing: `pypdf`
- AES support for encrypted PDFs: `cryptography`

## Project Structure

```text
11.PDF_APP/
  app.py
  requirements.txt
  src/
    pdf_app/
      __init__.py
      gui.py
      services/
        __init__.py
        pdf_service.py
      utils/
        __init__.py
        page_spec.py
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## Page Selection Format

Use 1-based page format in edit operations:

- `1` -> page 1
- `1,3,6` -> pages 1, 3, 6
- `2-5` -> pages 2 to 5
- `1,4-7,10`

For encrypted PDFs, use the `Password (optional)` field in the tab you are using.

For merge:
- Add one or more PDFs
- For each selected segment, set pages as `all` or `1,3-5,2`
- Reorder with `Move Up/Move Down`
- Use `Duplicate Selected` if you want multiple segments from the same PDF

## Notes

- This MVP focuses on practical core operations first.
- OCR, annotation drawing, and drag-and-drop can be added next.
