from __future__ import annotations

import io
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk

from src.pdf_app.services.pdf_service import (
    extract_pages,
    inspect_pdf,
    merge_pdf_segments,
    render_page_preview,
    read_page_text,
    remove_pages,
    rotate_pages,
)


PDF_FILETYPES = [("PDF files", "*.pdf")]


class ReaderTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent, padding=12)
        self.pdf_path_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.page_var = tk.StringVar(value="1")
        self.zoom_var = tk.StringVar(value="125%")
        self.total_pages = 0
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._build()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)

        ttk.Label(self, text="PDF file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.pdf_path_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(self, text="Browse", command=self._browse_pdf).grid(row=0, column=2)
        ttk.Button(self, text="Load", command=self._load_pdf_info).grid(
            row=0, column=3, padx=(8, 0)
        )

        ttk.Label(self, text="Password (optional):").grid(row=1, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.password_var, show="*").grid(
            row=1, column=1, sticky="ew", padx=(8, 8), pady=(8, 0)
        )

        self.info_text = ScrolledText(self, height=8, wrap="word")
        self.info_text.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(10, 8))
        self.info_text.configure(state="disabled")

        page_frame = ttk.Frame(self)
        page_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        page_frame.columnconfigure(8, weight=1)

        ttk.Label(page_frame, text="Page:").grid(row=0, column=0, sticky="w")
        self.page_spinbox = ttk.Spinbox(
            page_frame, from_=1, to=1, textvariable=self.page_var, width=8
        )
        self.page_spinbox.grid(row=0, column=1, sticky="w", padx=(6, 10))
        ttk.Button(page_frame, text="Prev", command=self._prev_page).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Button(page_frame, text="Next", command=self._next_page).grid(
            row=0, column=3, sticky="w", padx=(6, 10)
        )
        ttk.Label(page_frame, text="Zoom:").grid(row=0, column=4, sticky="w")
        self.zoom_combo = ttk.Combobox(
            page_frame,
            textvariable=self.zoom_var,
            values=["75%", "100%", "125%", "150%", "200%"],
            state="readonly",
            width=8,
        )
        self.zoom_combo.grid(row=0, column=5, sticky="w", padx=(6, 10))
        ttk.Button(page_frame, text="Render preview", command=self._render_page).grid(
            row=0, column=6, sticky="w"
        )
        ttk.Button(page_frame, text="Read page text", command=self._read_page).grid(
            row=0, column=7, sticky="w", padx=(8, 0)
        )

        content_notebook = ttk.Notebook(self)
        content_notebook.grid(row=4, column=0, columnspan=4, sticky="nsew")

        preview_tab = ttk.Frame(content_notebook, padding=4)
        preview_tab.columnconfigure(0, weight=1)
        preview_tab.rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(preview_tab, bg="#f2f2f2", highlightthickness=0)
        preview_vbar = ttk.Scrollbar(
            preview_tab, orient="vertical", command=self.preview_canvas.yview
        )
        preview_hbar = ttk.Scrollbar(
            preview_tab, orient="horizontal", command=self.preview_canvas.xview
        )
        self.preview_canvas.configure(
            yscrollcommand=preview_vbar.set, xscrollcommand=preview_hbar.set
        )

        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_vbar.grid(row=0, column=1, sticky="ns")
        preview_hbar.grid(row=1, column=0, sticky="ew")

        text_tab = ttk.Frame(content_notebook, padding=4)
        text_tab.columnconfigure(0, weight=1)
        text_tab.rowconfigure(0, weight=1)
        self.page_text = ScrolledText(text_tab, wrap="word")
        self.page_text.grid(row=0, column=0, sticky="nsew")
        self.page_text.configure(state="disabled")

        content_notebook.add(preview_tab, text="Visual Preview")
        content_notebook.add(text_tab, text="Extracted Text")

    def _browse_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=PDF_FILETYPES)
        if path:
            self.pdf_path_var.set(path)
            self._load_pdf_info()

    def _load_pdf_info(self) -> None:
        path = self.pdf_path_var.get().strip()
        if not path:
            messagebox.showwarning("Missing file", "Select a PDF file first.")
            return

        try:
            details = inspect_pdf(path, password=self._get_password())
            self.total_pages = int(details["pages"])
            self.page_spinbox.configure(to=max(1, self.total_pages))
            self.page_var.set("1")

            lines = [
                f"Path: {details['path']}",
                f"Pages: {details['pages']}",
                f"Encrypted: {details['encrypted']}",
                "",
                "Metadata:",
            ]
            metadata = details.get("metadata", {})
            if metadata:
                for key, value in metadata.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append("  [No metadata found]")

            self._set_text(self.info_text, "\n".join(lines))
            self._set_text(self.page_text, "")
            self.preview_canvas.delete("all")
            self._preview_photo = None
            self._render_page()
        except Exception as exc:
            messagebox.showerror("Failed to load PDF", str(exc))

    def _render_page(self) -> None:
        path = self.pdf_path_var.get().strip()
        if not path:
            messagebox.showwarning("Missing file", "Select a PDF file first.")
            return
        if self.total_pages < 1:
            messagebox.showwarning("No document loaded", "Load the PDF information first.")
            return

        try:
            page_number = self._get_page_number()
            zoom = self._get_zoom_factor()
            image_bytes = render_page_preview(
                path, page_number, zoom=zoom, password=self._get_password()
            )
            image = Image.open(io.BytesIO(image_bytes))
            self._preview_photo = ImageTk.PhotoImage(image)

            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor="nw", image=self._preview_photo)
            self.preview_canvas.configure(
                scrollregion=(0, 0, self._preview_photo.width(), self._preview_photo.height())
            )
            self.preview_canvas.xview_moveto(0)
            self.preview_canvas.yview_moveto(0)
        except Exception as exc:
            messagebox.showerror("Failed to render page", str(exc))

    def _read_page(self) -> None:
        path = self.pdf_path_var.get().strip()
        if not path:
            messagebox.showwarning("Missing file", "Select a PDF file first.")
            return
        if self.total_pages < 1:
            messagebox.showwarning("No document loaded", "Load the PDF information first.")
            return

        try:
            page_number = self._get_page_number()
            text = read_page_text(path, page_number, password=self._get_password())
            self._set_text(self.page_text, text)
        except Exception as exc:
            messagebox.showerror("Failed to read page", str(exc))

    def _prev_page(self) -> None:
        if self.total_pages < 1:
            return
        current = self._get_page_number_safe()
        self.page_var.set(str(max(1, current - 1)))
        self._render_page()

    def _next_page(self) -> None:
        if self.total_pages < 1:
            return
        current = self._get_page_number_safe()
        self.page_var.set(str(min(self.total_pages, current + 1)))
        self._render_page()

    def _get_page_number(self) -> int:
        value = int(self.page_var.get())
        if value < 1 or value > self.total_pages:
            raise ValueError(f"Page {value} is out of bounds (1-{self.total_pages}).")
        return value

    def _get_page_number_safe(self) -> int:
        try:
            value = int(self.page_var.get())
        except Exception:
            return 1
        return min(max(value, 1), max(self.total_pages, 1))

    def _get_zoom_factor(self) -> float:
        raw = self.zoom_var.get().strip().replace("%", "")
        if not raw:
            return 1.25
        value = float(raw)
        if value <= 0:
            raise ValueError("Zoom must be greater than 0.")
        return value / 100.0

    def _get_password(self) -> str | None:
        value = self.password_var.get()
        return value if value else None

    @staticmethod
    def _set_text(widget: ScrolledText, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.configure(state="disabled")


class MergeTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent, padding=12)
        self.output_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.page_spec_var = tk.StringVar(value="all")
        self.selected_info_var = tk.StringVar(
            value="Select a merge segment to edit pages."
        )
        self.segments: list[dict[str, str]] = []
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew")

        ttk.Button(controls, text="Add PDFs", command=self._add_files).pack(side="left")
        ttk.Button(
            controls, text="Duplicate Selected", command=self._duplicate_selected
        ).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Remove Selected", command=self._remove_selected).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(controls, text="Move Up", command=self._move_up).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(controls, text="Move Down", command=self._move_down).pack(
            side="left", padx=(8, 0)
        )

        self.files_list = tk.Listbox(self, selectmode=tk.SINGLE, exportselection=False)
        self.files_list.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        self.files_list.bind("<<ListboxSelect>>", self._on_select)

        page_row = ttk.Frame(self)
        page_row.grid(row=2, column=0, sticky="ew")
        page_row.columnconfigure(1, weight=1)
        ttk.Label(page_row, text="Pages for selected (all or 1,3-5,2):").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(page_row, textvariable=self.page_spec_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(page_row, text="Set Pages", command=self._set_pages_for_selected).grid(
            row=0, column=2, sticky="e"
        )
        ttk.Button(page_row, text="Set All", command=self._set_all_pages_for_selected).grid(
            row=0, column=3, sticky="e", padx=(8, 0)
        )

        ttk.Label(self, textvariable=self.selected_info_var).grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )

        password_row = ttk.Frame(self)
        password_row.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        password_row.columnconfigure(1, weight=1)
        ttk.Label(password_row, text="Password (optional):").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(password_row, textvariable=self.password_var, show="*").grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )

        output_row = ttk.Frame(self)
        output_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        output_row.columnconfigure(1, weight=1)

        ttk.Label(output_row, text="Output file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(output_row, textvariable=self.output_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(output_row, text="Browse", command=self._browse_output).grid(
            row=0, column=2
        )

        ttk.Button(self, text="Merge PDFs", command=self._merge).grid(
            row=6, column=0, sticky="e", pady=(10, 0)
        )

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=PDF_FILETYPES)
        if not paths:
            return

        start_idx = len(self.segments)
        for path in paths:
            self.segments.append({"path": path, "page_spec": "all"})
        self._refresh_list(select_index=start_idx)

    def _duplicate_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        self.segments.insert(idx + 1, self.segments[idx].copy())
        self._refresh_list(select_index=idx + 1)

    def _remove_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        self.segments.pop(idx)
        if not self.segments:
            self._refresh_list(select_index=None)
            self.page_spec_var.set("all")
            self.selected_info_var.set("Select a merge segment to edit pages.")
            return
        self._refresh_list(select_index=min(idx, len(self.segments) - 1))

    def _move_up(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        if idx == 0:
            return
        self.segments[idx - 1], self.segments[idx] = self.segments[idx], self.segments[idx - 1]
        self._refresh_list(select_index=idx - 1)

    def _move_down(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        if idx >= len(self.segments) - 1:
            return
        self.segments[idx + 1], self.segments[idx] = self.segments[idx], self.segments[idx + 1]
        self._refresh_list(select_index=idx + 1)

    def _set_pages_for_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showwarning("Missing selection", "Select a merge segment first.")
            return

        spec = self.page_spec_var.get().strip()
        if not spec:
            messagebox.showwarning("Missing pages", "Provide a page selection or 'all'.")
            return

        if spec.lower() in {"*", "all"}:
            spec = "all"
        self.segments[idx]["page_spec"] = spec
        self._refresh_list(select_index=idx)

    def _set_all_pages_for_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showwarning("Missing selection", "Select a merge segment first.")
            return
        self.segments[idx]["page_spec"] = "all"
        self.page_spec_var.set("all")
        self._refresh_list(select_index=idx)

    def _on_select(self, _event: object | None = None) -> None:
        idx = self._selected_index()
        if idx is None:
            self.selected_info_var.set("Select a merge segment to edit pages.")
            return
        selected = self.segments[idx]
        self.page_spec_var.set(selected.get("page_spec", "all"))
        self._update_selected_info(idx)

    def _update_selected_info(self, idx: int) -> None:
        item = self.segments[idx]
        self.selected_info_var.set(
            f"Selected #{idx + 1}: {item['path']} | pages: {item['page_spec']}"
        )

    def _refresh_list(self, select_index: int | None) -> None:
        self.files_list.delete(0, tk.END)
        for idx, item in enumerate(self.segments, start=1):
            file_name = Path(item["path"]).name
            page_spec = item.get("page_spec", "all")
            self.files_list.insert(tk.END, f"{idx:02d}. {file_name} | pages: {page_spec}")

        if select_index is None or not self.segments:
            return

        select_index = max(0, min(select_index, len(self.segments) - 1))
        self.files_list.selection_clear(0, tk.END)
        self.files_list.selection_set(select_index)
        self.files_list.activate(select_index)
        self.files_list.see(select_index)
        self._on_select()

    def _selected_index(self) -> int | None:
        selection = self.files_list.curselection()
        if not selection:
            return None
        return int(selection[0])

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=PDF_FILETYPES
        )
        if path:
            self.output_var.set(path)

    def _merge(self) -> None:
        output = self.output_var.get().strip()

        if not self.segments:
            messagebox.showwarning("Missing files", "Add at least one merge segment.")
            return
        if not output:
            messagebox.showwarning("Missing output", "Select an output PDF file.")
            return

        try:
            merge_pdf_segments(self.segments, output, password=self._get_password())
            messagebox.showinfo("Success", f"Merged PDF saved to:\n{output}")
        except Exception as exc:
            messagebox.showerror("Merge failed", str(exc))

    def _get_password(self) -> str | None:
        value = self.password_var.get()
        return value if value else None


class EditTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook) -> None:
        super().__init__(parent, padding=12)
        self.input_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.page_spec_var = tk.StringVar()
        self.operation_var = tk.StringVar(value="Rotate")
        self.angle_var = tk.StringVar(value="90")
        self._build()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Input PDF:").grid(row=0, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.input_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        ttk.Button(self, text="Browse", command=self._browse_input).grid(row=0, column=2)

        ttk.Label(self, text="Password (optional):").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(self, textvariable=self.password_var, show="*").grid(
            row=1, column=1, sticky="ew", pady=(10, 0), padx=(0, 8)
        )

        ttk.Label(self, text="Operation:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        operation_combo = ttk.Combobox(
            self,
            textvariable=self.operation_var,
            state="readonly",
            values=["Rotate", "Remove", "Extract"],
            width=12,
        )
        operation_combo.grid(row=2, column=1, sticky="w", pady=(10, 0))
        operation_combo.bind("<<ComboboxSelected>>", self._update_angle_state)

        ttk.Label(self, text="Pages (e.g. 1,3-5):").grid(
            row=3, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(self, textvariable=self.page_spec_var).grid(
            row=3, column=1, sticky="ew", pady=(10, 0)
        )

        ttk.Label(self, text="Angle:").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.angle_combo = ttk.Combobox(
            self, textvariable=self.angle_var, state="readonly", values=["90", "180", "270"]
        )
        self.angle_combo.grid(row=4, column=1, sticky="w", pady=(10, 0))

        ttk.Label(self, text="Output PDF:").grid(row=5, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(self, textvariable=self.output_var).grid(
            row=5, column=1, sticky="ew", pady=(10, 0), padx=(0, 8)
        )
        ttk.Button(self, text="Browse", command=self._browse_output).grid(
            row=5, column=2, pady=(10, 0)
        )

        ttk.Button(self, text="Apply", command=self._apply_edit).grid(
            row=6, column=2, sticky="e", pady=(14, 0)
        )

        self._update_angle_state()

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=PDF_FILETYPES)
        if path:
            self.input_var.set(path)
            if not self.output_var.get().strip():
                self.output_var.set(path.replace(".pdf", "_edited.pdf"))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=PDF_FILETYPES
        )
        if path:
            self.output_var.set(path)

    def _update_angle_state(self, _event: object | None = None) -> None:
        is_rotate = self.operation_var.get() == "Rotate"
        self.angle_combo.configure(state="readonly" if is_rotate else "disabled")

    def _apply_edit(self) -> None:
        input_path = self.input_var.get().strip()
        output_path = self.output_var.get().strip()
        pages = self.page_spec_var.get().strip()
        operation = self.operation_var.get()

        if not input_path:
            messagebox.showwarning("Missing input", "Select an input PDF file.")
            return
        if not output_path:
            messagebox.showwarning("Missing output", "Select an output PDF file.")
            return
        if not pages:
            messagebox.showwarning("Missing pages", "Provide page selection.")
            return

        try:
            if operation == "Rotate":
                rotate_pages(
                    input_path,
                    output_path,
                    pages,
                    int(self.angle_var.get()),
                    password=self._get_password(),
                )
            elif operation == "Remove":
                remove_pages(input_path, output_path, pages, password=self._get_password())
            elif operation == "Extract":
                extract_pages(input_path, output_path, pages, password=self._get_password())
            else:
                raise ValueError(f"Unknown operation: {operation}")

            messagebox.showinfo("Success", f"Edited PDF saved to:\n{output_path}")
        except Exception as exc:
            messagebox.showerror("Edit failed", str(exc))

    def _get_password(self) -> str | None:
        value = self.password_var.get()
        return value if value else None


class PDFDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Desktop App")
        self.geometry("920x680")
        self.minsize(760, 520)
        self._build()

    def _build(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        notebook.add(ReaderTab(notebook), text="Read")
        notebook.add(MergeTab(notebook), text="Merge")
        notebook.add(EditTab(notebook), text="Edit")


def launch_app() -> None:
    app = PDFDesktopApp()
    app.mainloop()
