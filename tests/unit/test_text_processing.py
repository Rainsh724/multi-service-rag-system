
import pytest

from services.document_service.app.services.pdf_extractor import ExtractedPage
from services.document_service.app.services.text_cleaner import TextCleaner
from services.document_service.app.services.chunker import TextChunker


def test_text_cleaner_normalizes_persian_characters():
    cleaner = TextCleaner()

    result = cleaner.clean("كتاب عربي ي")

    assert result == "کتاب عربی ی"


def test_text_cleaner_preserves_paragraphs():
    cleaner = TextCleaner()

    result = cleaner.clean("First paragraph.\n\n\nSecond paragraph.")

    assert result == "First paragraph.\n\nSecond paragraph."


def test_chunker_preserves_page_numbers():
    chunker = TextChunker(
        chunk_size=50,
        chunk_overlap=10,
    )

    pages = [
        ExtractedPage(
            page_number=1,
            text="This is the first page. " * 5,
        ),
        ExtractedPage(
            page_number=2,
            text="This is the second page. " * 5,
        ),
    ]

    chunks = chunker.chunk_pages(pages)

    assert len(chunks) > 2
    assert all(chunk.page_number in (1, 2) for chunk in chunks)

    assert any(chunk.page_number == 1 for chunk in chunks)
    assert any(chunk.page_number == 2 for chunk in chunks)


def test_chunker_respects_maximum_size():
    chunker = TextChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    pages = [
        ExtractedPage(
            page_number=1,
            text="word " * 200,
        )
    ]

    chunks = chunker.chunk_pages(pages)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 100 for chunk in chunks)


def test_chunker_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        TextChunker(
            chunk_size=100,
            chunk_overlap=100,
        )


def test_chunker_splits_tokens_longer_than_chunk_size():
    chunker = TextChunker(
        chunk_size=10,
        chunk_overlap=2,
    )
    long_token = "abcdefghijklmno"

    chunks = chunker.chunk_pages([
        ExtractedPage(page_number=1, text=long_token),
    ])

    assert "".join(chunk.text for chunk in chunks) == long_token
    assert all(len(chunk.text) <= 10 for chunk in chunks)
