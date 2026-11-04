from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from services.retrieval_service.app.repositories.chunk_repository import (
    ChunkRepository,
)
from shared.schemas.retrieval import ChunkInput, IndexRequest


def make_index_request() -> IndexRequest:
    return IndexRequest(
        document_id=uuid4(),
        filename="sample.pdf",
        chunks=[
            ChunkInput(
                chunk_id=uuid4(),
                text="First chunk",
                embedding=[0.1] * 768,
                page_number=1,
                chunk_index=0,
            ),
            ChunkInput(
                chunk_id=uuid4(),
                text="Second chunk",
                embedding=[0.2] * 768,
                page_number=1,
                chunk_index=1,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_reindex_deletes_old_chunks_before_inserting_new_ones():
    session = AsyncMock()
    session.execute.side_effect = [
        SimpleNamespace(rowcount=2),
        SimpleNamespace(rowcount=2),
    ]
    request = make_index_request()

    indexed_count = await ChunkRepository.index_chunks(session, request)

    delete_statement, insert_statement = [
        call.args[0] for call in session.execute.await_args_list
    ]
    delete_sql = str(
        delete_statement.compile(dialect=postgresql.dialect())
    )
    insert_sql = str(
        insert_statement.compile(dialect=postgresql.dialect())
    )

    assert "DELETE FROM chunks" in delete_sql
    assert "document_id" in delete_sql
    assert "INSERT INTO chunks" in insert_sql
    assert indexed_count == 2
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_reindex_rolls_back_when_insert_fails():
    session = AsyncMock()
    session.execute.side_effect = [
        SimpleNamespace(rowcount=2),
        RuntimeError("database insert failed"),
    ]

    with pytest.raises(RuntimeError, match="database insert failed"):
        await ChunkRepository.index_chunks(session, make_index_request())

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()
