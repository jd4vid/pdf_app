from __future__ import annotations


def parse_page_spec(spec: str, total_pages: int) -> set[int]:
    """
    Parse a 1-based page specification into zero-based page indexes.

    Examples:
    - "1"
    - "1,3,5"
    - "2-4"
    - "1,3-5,8"
    """
    if total_pages < 1:
        raise ValueError("Document has no pages.")

    cleaned = spec.strip()
    if not cleaned:
        raise ValueError("Page selection is empty.")

    indexes: set[int] = set()
    chunks = [chunk.strip() for chunk in cleaned.split(",") if chunk.strip()]

    if not chunks:
        raise ValueError("Invalid page selection format.")

    for chunk in chunks:
        if "-" in chunk:
            parts = [part.strip() for part in chunk.split("-")]
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                raise ValueError(f"Invalid range '{chunk}'.")

            start = int(parts[0])
            end = int(parts[1])
            if start > end:
                raise ValueError(f"Invalid range '{chunk}' (start > end).")

            for page_num in range(start, end + 1):
                if page_num < 1 or page_num > total_pages:
                    raise ValueError(
                        f"Page {page_num} is out of bounds (1-{total_pages})."
                    )
                indexes.add(page_num - 1)
        else:
            if not chunk.isdigit():
                raise ValueError(f"Invalid page '{chunk}'.")
            page_num = int(chunk)
            if page_num < 1 or page_num > total_pages:
                raise ValueError(f"Page {page_num} is out of bounds (1-{total_pages}).")
            indexes.add(page_num - 1)

    if not indexes:
        raise ValueError("No valid pages selected.")

    return indexes


def parse_page_sequence(spec: str, total_pages: int) -> list[int]:
    """
    Parse a 1-based page specification into an ordered zero-based list.

    Unlike `parse_page_spec`, this preserves order and duplicates.
    Examples:
    - "1,3,2" -> [0, 2, 1]
    - "2-4,1" -> [1, 2, 3, 0]
    """
    if total_pages < 1:
        raise ValueError("Document has no pages.")

    cleaned = spec.strip()
    if not cleaned:
        raise ValueError("Page selection is empty.")

    indexes: list[int] = []
    chunks = [chunk.strip() for chunk in cleaned.split(",") if chunk.strip()]
    if not chunks:
        raise ValueError("Invalid page selection format.")

    for chunk in chunks:
        if "-" in chunk:
            parts = [part.strip() for part in chunk.split("-")]
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                raise ValueError(f"Invalid range '{chunk}'.")

            start = int(parts[0])
            end = int(parts[1])
            if start > end:
                raise ValueError(f"Invalid range '{chunk}' (start > end).")

            for page_num in range(start, end + 1):
                if page_num < 1 or page_num > total_pages:
                    raise ValueError(
                        f"Page {page_num} is out of bounds (1-{total_pages})."
                    )
                indexes.append(page_num - 1)
        else:
            if not chunk.isdigit():
                raise ValueError(f"Invalid page '{chunk}'.")

            page_num = int(chunk)
            if page_num < 1 or page_num > total_pages:
                raise ValueError(f"Page {page_num} is out of bounds (1-{total_pages}).")
            indexes.append(page_num - 1)

    if not indexes:
        raise ValueError("No valid pages selected.")

    return indexes
