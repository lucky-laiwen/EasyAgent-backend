from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CreateKnowledgeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: str = Field("", max_length=500, description="知识库描述")


class UpdateKnowledgeBase(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")


class KnowledgeBaseItem(BaseModel):
    id: int = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: str = Field(..., description="知识库描述")
    chroma_collection: str = Field(..., description="ChromaDB collection 名称")
    created_at: datetime = Field(..., description="创建时间")
    doc_count: int = Field(0, description="文档数量")

    class Config:
        from_attributes = True


class DocumentItem(BaseModel):
    id: int = Field(..., description="文档ID")
    kb_id: int = Field(..., description="所属知识库ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    chunk_count: int = Field(0, description="分块数量")
    status: str = Field(..., description="处理状态")
    created_at: datetime = Field(..., description="上传时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class BindKnowledgeBase(BaseModel):
    chat_id: int = Field(..., description="聊天会话ID")
    kb_id: int = Field(..., description="知识库ID")


class UnbindKnowledgeBase(BaseModel):
    chat_id: int = Field(..., description="聊天会话ID")


class ReferenceItem(BaseModel):
    doc_id: int = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    chunk_index: int = Field(..., description="chunk 序号")
    snippet: str = Field(..., description="文本片段（前150-200字）")
