
from pathlib import Path

import pytest

from services.document_service.app.services.pdf_extractor import (
    PDFExtractor,
    PDFNoTextError,
)


def test_extract_pdf_pages():
    pdf_path = Path("tests/samples/tasks-RAG.pdf")

    extractor = PDFExtractor()
    pages = extractor.extract(str(pdf_path))

    assert len(pages) > 0
    assert pages[0].page_number == 1

    for page in pages:
        assert page.page_number >= 1
        assert isinstance(page.text, str)

    print(f"Extracted pages: {len(pages)}")
    print(f"First page preview:\n{pages[0].text[:500]}")


def test_missing_pdf():
    extractor = PDFExtractor()

    with pytest.raises(FileNotFoundError):
        extractor.extract("sample_pdfs/nonexistent.pdf")
