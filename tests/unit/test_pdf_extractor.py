import pymupdf
import pytest

from services.document_service.app.services.pdf_extractor import (
    PDFExtractor,
    PDFNoTextError,
)


def test_extract_pdf_pages(tmp_path):
    pdf_path = tmp_path / "sample.pdf"

    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), "A small PDF fixture for extraction.")
        pdf.save(pdf_path)

    pages = PDFExtractor().extract(str(pdf_path))

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "small PDF fixture" in pages[0].text


def test_missing_pdf():
    extractor = PDFExtractor()

    with pytest.raises(FileNotFoundError):
        extractor.extract("sample_pdfs/nonexistent.pdf")


def test_pdf_without_extractable_text(tmp_path):
    pdf_path = tmp_path / "empty.pdf"

    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(pdf_path)

    with pytest.raises(PDFNoTextError):
        PDFExtractor().extract(str(pdf_path))
