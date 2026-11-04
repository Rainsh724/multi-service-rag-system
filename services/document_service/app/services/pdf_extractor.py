
from dataclasses import dataclass
from pathlib import Path

import pymupdf


class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors."""


class PDFEncryptedError(PDFExtractionError):
    """Raised when the PDF is password-protected."""


class PDFNoTextError(PDFExtractionError):
    """Raised when the PDF contains no extractable text."""


@dataclass
class ExtractedPage:
    page_number: int
    text: str


class PDFExtractor:

    def _validate_pdf_signature(self, path: Path) -> None:
        with path.open("rb") as file:
            header = file.read(1024)

        if b"%PDF-" not in header:
            raise PDFExtractionError(
                "Invalid PDF file signature."
            )

    def extract(self, file_path: str) -> list[ExtractedPage]:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"PDF file not found: {path}"
            )

        if not path.is_file():
            raise PDFExtractionError(
                "The provided path is not a file."
            )

        try:
            self._validate_pdf_signature(path)
            
            with pymupdf.open(path) as pdf:

                if pdf.is_encrypted:
                    raise PDFEncryptedError(
                        "Password-protected PDFs are not supported."
                    )

                extracted_pages = []

                for page_index, page in enumerate(pdf):
                    text = page.get_text(
                        "text",
                        sort=False,
                    )

                    extracted_pages.append(
                        ExtractedPage(
                            page_number=page_index + 1,
                            text=text,
                        )
                    )

                if not any(
                    page.text.strip()
                    for page in extracted_pages
                ):
                    raise PDFNoTextError(
                        "No extractable text found in the PDF. "
                        "The document may contain scanned images."
                    )

                return extracted_pages

        except PDFExtractionError:
            raise

        except Exception as exc:
            raise PDFExtractionError(
                f"Failed to extract PDF content: {exc}"
            ) from exc
