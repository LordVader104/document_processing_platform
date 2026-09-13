import pymupdf


def load_pdf_pages(file_path):
    document = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(document):
        text = page.get_text()

        if text:
            pages.append({
                "page": page_number + 1,
                "text": text
            })

    document.close()

    return pages



#old codes good for learning but bad performance nevertheless im keeping them because it was good execise to learn multi processing
"""
import time
from concurrent.futures import ProcessPoolExecutor
from pypdf import PdfReader


def _extract_page_range(args):
    file_path, start_page, end_page = args

    reader = PdfReader(file_path)
    pages = []

    for page_index in range(start_page, end_page):
        page = reader.pages[page_index]
        page_text = page.extract_text()

        if page_text:
            pages.append({
                "page": page_index + 1,
                "text": page_text
            })

    return pages


def load_pdf_pages(file_path, workers=12):

    start = time.perf_counter()

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)

    chunk_size = (total_pages + workers - 1) // workers

    ranges = []

    for start_page in range(0, total_pages, chunk_size):
        end_page = min(
            start_page + chunk_size,
            total_pages
        )

        ranges.append(
            (str(file_path), start_page, end_page)
        )

    with ProcessPoolExecutor(max_workers=workers) as executor:
        chunks = list(
            executor.map(
                _extract_page_range,
                ranges
            )
        )

    pages = []

    for chunk in chunks:
        pages.extend(chunk)

    elapsed = time.perf_counter() - start

    print(
        f"[PDF] {file_path.name}: "
        f"{total_pages} pages extracted "
        f"in {elapsed:.2f}s "
        f"with {workers} processes"
    )

    return pages


def load_pdf(file_path):
    pages = load_pdf_pages(file_path)

    return "\n".join(
        page["text"]
        for page in pages
    )
"""