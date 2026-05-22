from sqlalchemy.orm import Session
from typing import Optional, List
from models.knowledge import KnowledgeBase, KnowledgeDocument
from models.chat import Chat


# === Knowledge Base CRUD ===

def create_knowledge_base(db: Session, user_id: int, name: str, description: str = "") -> KnowledgeBase:
    kb = KnowledgeBase(
        user_id=user_id,
        name=name,
        description=description,
        chroma_collection="",  # will be set after commit with id
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    kb.chroma_collection = f"kb_{kb.id}"
    db.commit()
    db.refresh(kb)
    return kb


def get_or_create_global_kb(db: Session, user_id: int) -> KnowledgeBase:
    """获取用户的全局知识库，不存在则自动创建。"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == user_id,
        KnowledgeBase.name == "__global__"
    ).first()
    if not kb:
        kb = create_knowledge_base(db, user_id, "__global__", "全局知识库")
    return kb


def get_kb_by_id(db: Session, kb_id: int, user_id: int) -> Optional[KnowledgeBase]:
    return db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.user_id == user_id
    ).first()


def get_kb_list(db: Session, user_id: int) -> List[KnowledgeBase]:
    return db.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == user_id
    ).order_by(KnowledgeBase.id.desc()).all()


def update_knowledge_base(db: Session, kb_id: int, user_id: int, name: str = None, description: str = None) -> Optional[KnowledgeBase]:
    kb = get_kb_by_id(db, kb_id, user_id)
    if not kb:
        return None
    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description
    db.commit()
    db.refresh(kb)
    return kb


def delete_knowledge_base(db: Session, kb_id: int, user_id: int) -> bool:
    kb = get_kb_by_id(db, kb_id, user_id)
    if not kb:
        return False
    db.delete(kb)
    db.commit()
    return True


def get_docs_by_status(db: Session, kb_id: int, status: str) -> List[KnowledgeDocument]:
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.kb_id == kb_id,
        KnowledgeDocument.status == status
    ).all()


# === Document CRUD ===

def create_document(db: Session, kb_id: int, filename: str, file_type: str) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        kb_id=kb_id,
        filename=filename,
        file_type=file_type,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_doc_by_id(db: Session, doc_id: int) -> Optional[KnowledgeDocument]:
    return db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()


def get_doc_list(db: Session, kb_id: int) -> List[KnowledgeDocument]:
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.kb_id == kb_id
    ).order_by(KnowledgeDocument.id.desc()).all()


def update_document_status(db: Session, doc_id: int, status: str, chunk_count: int = 0) -> Optional[KnowledgeDocument]:
    doc = get_doc_by_id(db, doc_id)
    if not doc:
        return None
    doc.status = status
    doc.chunk_count = chunk_count
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, doc_id: int) -> Optional[KnowledgeDocument]:
    doc = get_doc_by_id(db, doc_id)
    if not doc:
        return None
    db.delete(doc)
    db.commit()
    return doc


# === Chat KB Binding ===

def bind_kb_to_chat(db: Session, chat_id: int, kb_id: int, user_id: int) -> Optional[Chat]:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        return None
    chat.kb_id = kb_id
    db.commit()
    db.refresh(chat)
    return chat


def unbind_kb_from_chat(db: Session, chat_id: int, user_id: int) -> Optional[Chat]:
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        return None
    chat.kb_id = None
    db.commit()
    db.refresh(chat)
    return chat


def get_chat_kb_id(db: Session, chat_id: int) -> Optional[int]:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return None
    return chat.kb_id


def get_doc_count(db: Session, kb_id: int) -> int:
    return db.query(KnowledgeDocument).filter(KnowledgeDocument.kb_id == kb_id).count()


def get_global_doc_list(db: Session, user_id: int) -> List[KnowledgeDocument]:
    """获取用户的全局文档（未绑定到任何会话和消息的文档）。"""
    kb = get_or_create_global_kb(db, user_id)
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.kb_id == kb.id,
        KnowledgeDocument.chat_id.is_(None),
        KnowledgeDocument.message_id.is_(None)
    ).order_by(KnowledgeDocument.id.desc()).all()


def get_chat_doc_list(db: Session, chat_id: int) -> List[KnowledgeDocument]:
    """获取会话专属文档（已绑定到消息的文档）。"""
    return db.query(KnowledgeDocument).filter(
        KnowledgeDocument.chat_id == chat_id,
        KnowledgeDocument.message_id.isnot(None)
    ).order_by(KnowledgeDocument.id.desc()).all()


def bind_docs_to_message(db: Session, doc_ids: List[int], chat_id: int, message_id: int) -> List[KnowledgeDocument]:
    """将文档绑定到指定的消息和会话。"""
    docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.id.in_(doc_ids)).all()
    for doc in docs:
        doc.chat_id = chat_id
        doc.message_id = message_id
    db.commit()
    for doc in docs:
        db.refresh(doc)
    return docs
