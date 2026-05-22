import os
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from utils.utils import get_current_user
from schemas.response import ResponseSchema
from schemas.knowledge import DocumentItem
from models.knowledge import KnowledgeDocument
from crud.knowledge import (
    get_or_create_global_kb, get_kb_by_id,
    create_document, get_doc_by_id,
    get_doc_list, get_global_doc_list, get_chat_doc_list,
    update_document_status, delete_document,
)
from utils.document_parser import parse_document, validate_file
from utils.rag_service import get_rag_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Concurrency limiter for embedding tasks
embedding_semaphore = asyncio.Semaphore(2)


async def process_document_async(doc_id: int, kb_collection: str):
    """Background task: split, embed, store in ChromaDB."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        rag = get_rag_service()
        doc = get_doc_by_id(db, doc_id)
        if not doc:
            return

        chunks = rag.split_text(doc.filename)  # placeholder, actual text not stored
        # Re-read text from ChromaDB is not possible, so we need to store text temporarily
        # Actually, we need the text. Let me reconsider.
        update_document_status(db, doc_id, "failed")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Document processing failed for doc {doc_id}: {e}")
        update_document_status(db, doc_id, "failed")
    finally:
        db.close()


async def process_document_with_text(doc_id: int, kb_collection: str, text: str, filename: str):
    """Background task: split, embed, store in ChromaDB."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        rag = get_rag_service()
        chunks = rag.split_text(text)
        if not chunks:
            update_document_status(db, doc_id, "failed")
            return

        async with embedding_semaphore:
            chunk_count = rag.embed_and_store(
                collection_name=kb_collection,
                chunks=chunks,
                doc_id=doc_id,
                filename=filename,
            )

        update_document_status(db, doc_id, "completed", chunk_count)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Document processing failed for doc {doc_id}: {e}")
        update_document_status(db, doc_id, "failed")
    finally:
        db.close()


def _to_doc_item(doc: KnowledgeDocument) -> DocumentItem:
    return DocumentItem(
        id=doc.id, kb_id=doc.kb_id, filename=doc.filename,
        file_type=doc.file_type, chunk_count=doc.chunk_count,
        status=doc.status, created_at=doc.created_at, updated_at=doc.updated_at,
    )


# === 全局知识库文档管理 ===

@router.post("/upload_doc", response_model=ResponseSchema)
async def upload_global_doc_router(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: int = Depends(get_current_user),
):
    """上传文档到全局知识库，所有对话可用。"""
    kb = get_or_create_global_kb(db, user)

    content = await file.read()
    error = validate_file(file.filename, len(content))
    if error:
        return ResponseSchema.fail(message=error, status=400)

    try:
        text = parse_document(file.filename, content)
    except Exception as e:
        return ResponseSchema.fail(message=f"文档解析失败: {str(e)}", status=400)

    if not text.strip():
        return ResponseSchema.fail(message="文档内容为空", status=400)

    file_type = os.path.splitext(file.filename)[1].lower().lstrip(".")
    doc = create_document(db, kb.id, file.filename, file_type)

    background_tasks.add_task(
        process_document_with_text, doc.id, kb.chroma_collection, text, file.filename
    )

    return ResponseSchema.ok(message="文档已上传，正在处理中", data=_to_doc_item(doc))


@router.get("/get_doc_list", response_model=ResponseSchema)
async def get_global_doc_list_router(
    db: Session = Depends(get_db),
    user: int = Depends(get_current_user),
):
    """获取全局知识库的文档列表。"""
    docs = get_global_doc_list(db, user)
    return ResponseSchema.ok(message="查询成功", data=[_to_doc_item(d) for d in docs])


# === 会话专属文档管理 ===


@router.get("/get_chat_doc_list/{chat_id}", response_model=ResponseSchema)
async def get_chat_doc_list_router(
    chat_id: int,
    db: Session = Depends(get_db),
    user: int = Depends(get_current_user),
):
    """获取会话专属文档列表。"""
    docs = get_chat_doc_list(db, chat_id)
    return ResponseSchema.ok(message="查询成功", data=[_to_doc_item(d) for d in docs])


# === 通用文档操作 ===

@router.delete("/delete_doc/{doc_id}", response_model=ResponseSchema)
async def delete_doc_router(
    doc_id: int,
    db: Session = Depends(get_db),
    user: int = Depends(get_current_user),
):
    doc = get_doc_by_id(db, doc_id)
    if not doc:
        return ResponseSchema.fail(message="文档不存在", status=404)

    kb = get_kb_by_id(db, doc.kb_id, user)
    if not kb:
        return ResponseSchema.fail(message="知识库不存在", status=404)

    rag = get_rag_service()
    rag.delete_doc_chunks(kb.chroma_collection, doc_id)
    delete_document(db, doc_id)
    return ResponseSchema.ok(message="删除成功", data=None)


@router.get("/get_doc_content/{doc_id}", response_model=ResponseSchema)
async def get_doc_content_router(
    doc_id: int,
    db: Session = Depends(get_db),
    user: int = Depends(get_current_user),
):
    doc = get_doc_by_id(db, doc_id)
    if not doc:
        return ResponseSchema.fail(message="文档不存在", status=404)

    if doc.status != "completed":
        return ResponseSchema.fail(message="文档尚未处理完成", status=400)

    kb = get_kb_by_id(db, doc.kb_id, user)
    if not kb:
        return ResponseSchema.fail(message="知识库不存在", status=404)

    rag = get_rag_service()
    chunks = rag.get_doc_chunks(kb.chroma_collection, doc_id)

    return ResponseSchema.ok(message="查询成功", data={
        "doc_id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "chunk_count": len(chunks),
        "chunks": chunks,
    })


@router.post("/retry_doc/{doc_id}", response_model=ResponseSchema)
async def retry_doc_router(
    doc_id: int,
    db: Session = Depends(get_db),
    user: int = Depends(get_current_user),
):
    doc = get_doc_by_id(db, doc_id)
    if not doc:
        return ResponseSchema.fail(message="文档不存在", status=404)

    if doc.status == "completed":
        return ResponseSchema.fail(message="文档已处理完成，无需重试", status=400)
    if doc.status == "processing":
        return ResponseSchema.fail(message="文档正在处理中，请稍后再试", status=400)

    kb = get_kb_by_id(db, doc.kb_id, user)
    if not kb:
        return ResponseSchema.fail(message="知识库不存在", status=404)

    rag = get_rag_service()
    rag.delete_doc_chunks(kb.chroma_collection, doc_id)
    update_document_status(db, doc_id, "processing")

    return ResponseSchema.fail(message="请重新上传文档以重试", status=400)
