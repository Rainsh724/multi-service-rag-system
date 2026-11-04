import re
from dataclasses import dataclass

from services.document_service.app.services.pdf_extractor import (
    ExtractedPage,
)


@dataclass
class TextChunk:
    chunk_index: int
    page_number: int
    text: str


class TextChunker:

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative.")

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(
        self,
        pages: list[ExtractedPage],
    ) -> list[TextChunk]:

        chunks = []

        for page in pages:
            text = page.text.strip()

            if not text:
                continue

            for chunk_text in self._chunk_text(text):
                chunks.append(
                    TextChunk(
                        chunk_index=len(chunks),
                        page_number=page.page_number,
                        text=chunk_text,
                    )
                )

        return chunks

    def _chunk_text(self, text: str) -> list[str]:
        sentences = re.split(
            r"(?<=[.!?؟؛])\s+|\n{2,}",
            text,
        )

        chunks = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            for part in self._split_long_text(sentence):
                candidate = f"{current} {part}".strip() if current else part

                if len(candidate) <= self.chunk_size:
                    current = candidate
                    continue

                if current:
                    chunks.append(current)

                overlap = self._create_overlap(current)
                candidate = f"{overlap} {part}".strip() if overlap else part

                if len(candidate) <= self.chunk_size:
                    current = candidate
                else:
                    chunks.append(part)
                    current = ""

        if current:
            chunks.append(current)

        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        parts = []
        current = ""

        for word in text.split():
            if len(word) > self.chunk_size:
                if current:
                    parts.append(current)
                    current = ""

                parts.extend(
                    word[index:index + self.chunk_size]
                    for index in range(0, len(word), self.chunk_size)
                )
                continue

            candidate = f"{current} {word}".strip() if current else word

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    parts.append(current)
                current = word

        if current:
            parts.append(current)

        return parts

    def _create_overlap(self, text: str) -> str:
        if self.chunk_overlap == 0:
            return ""

        words = text.split()
        overlap_words = []
        overlap_length = 0

        for word in reversed(words):
            added_length = len(word) + (1 if overlap_words else 0)

            if overlap_length + added_length > self.chunk_overlap:
                break

            overlap_words.insert(0, word)
            overlap_length += added_length

        return " ".join(overlap_words)
