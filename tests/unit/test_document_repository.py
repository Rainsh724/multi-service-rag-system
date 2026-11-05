from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from services.document_service.app.repositories.document_repository import (
    DocumentRepository,
)


@pytest.mark.asyncio
async def test_list_all_returns_documents_newest_first():
    documents = [SimpleNamespace(id="new"), SimpleNamespace(id="old")]
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: documents)
    )

    result = await DocumentRepository.list_all(session)

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert result == documents
    assert "ORDER BY documents.created_at DESC" in sql
