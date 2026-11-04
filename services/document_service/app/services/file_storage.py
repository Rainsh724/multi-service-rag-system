import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from services.document_service.app.core.config import settings


class FileStorage:

    def __init__(self):
        self.base_path = Path(settings.storage_path)

    async def save(
        self,
        file: UploadFile,
        document_id: UUID,
    ) -> tuple[str, str]:
        self.base_path.mkdir(parents=True, exist_ok=True)

        document_dir = self.base_path / str(document_id)
        document_dir.mkdir(parents=True, exist_ok=True)

        file_path = document_dir / "original.pdf"

        sha256 = hashlib.sha256()
        total_size = 0
        max_size = settings.max_file_size_mb * 1024 * 1024

        try:
            with file_path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)

                    if total_size > max_size:
                        raise ValueError("File exceeds maximum allowed size.")

                    sha256.update(chunk)
                    output.write(chunk)

        except Exception:
            if file_path.exists():
                file_path.unlink()

            if document_dir.exists() and not any(document_dir.iterdir()):
                document_dir.rmdir()

            raise

        return str(file_path), sha256.hexdigest()

    async def delete(self, file_path: str) -> None:
        path = Path(file_path)

        if path.exists():
            path.unlink()

        if path.parent.exists() and not any(path.parent.iterdir()):
            path.parent.rmdir()