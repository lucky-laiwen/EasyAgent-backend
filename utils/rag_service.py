import re
import logging
from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

logger = logging.getLogger(__name__)

# Chunking config
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]

# Retrieval config
DEFAULT_TOP_K = 3
MAX_TOP_K = 10

# Prompt injection defense
SANITIZE_MAX_LEN = 2000


class RagService:
    def __init__(self, ollama_base_url: str = "http://localhost:11434", embedding_model: str = "qwen3-embedding:8b"):
        import chromadb
        self.chroma_client = chromadb.PersistentClient(path="./chroma_data/")
        self.embeddings = OllamaEmbeddings(model=embedding_model, base_url=ollama_base_url)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=SEPARATORS,
        )
        self._verify_embedding_dimension()

    def _verify_embedding_dimension(self):
        """Verify embedding dimension on startup."""
        try:
            test_vec = self.embeddings.embed_query("test")
            logger.info(f"Embedding model output dimension: {len(test_vec)}")
        except Exception as e:
            logger.warning(f"Embedding dimension check failed (Ollama may not be running): {e}")

    def get_or_create_collection(self, collection_name: str):
        """Get or create a ChromaDB collection."""
        return self.chroma_client.get_or_create_collection(name=collection_name)

    def delete_collection(self, collection_name: str):
        """Delete a ChromaDB collection."""
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception as e:
            logger.warning(f"Failed to delete collection {collection_name}: {e}")

    def split_text(self, text: str) -> List:
        """Split text into chunks using RecursiveCharacterTextSplitter."""
        from langchain_core.documents import Document
        docs = [Document(page_content=text)]
        return self.text_splitter.split_documents(docs)

    def embed_and_store(self, collection_name: str, chunks: list, doc_id: int, filename: str) -> int:
        """Embed chunks and store in ChromaDB. Returns chunk count."""
        if not chunks:
            return 0

        collection = self.get_or_create_collection(collection_name)

        texts = [c.page_content for c in chunks]
        vectors = self.embeddings.embed_documents(texts)

        ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": doc_id, "filename": filename, "chunk_index": i}
            for i in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )

        return len(chunks)

    def delete_doc_chunks(self, collection_name: str, doc_id: int):
        """Delete all chunks belonging to a document from ChromaDB."""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            logger.warning(f"Failed to delete chunks for doc {doc_id}: {e}")

    def get_doc_chunks(self, collection_name: str, doc_id: int) -> List[dict]:
        """Get all chunks belonging to a document from ChromaDB."""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception:
            return []

        results = collection.get(
            where={"doc_id": doc_id},
            include=["documents", "metadatas"],
        )

        chunks = []
        if results and results["documents"]:
            for doc, meta in zip(results["documents"], results["metadatas"]):
                chunks.append({
                    "content": doc,
                    "chunk_index": meta.get("chunk_index"),
                })

        # Sort by chunk_index
        chunks.sort(key=lambda c: c.get("chunk_index", 0))
        return chunks

    def retrieve(self, collection_name: str, query: str, top_k: int = DEFAULT_TOP_K, doc_ids: List[int] = None) -> List[dict]:
        """Retrieve top_k most similar chunks for a query.

        Args:
            collection_name: ChromaDB collection name
            query: User query text
            top_k: Number of results to return
            doc_ids: Optional list of document IDs to filter by. If None, searches entire collection.
        """
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception:
            return []

        if collection.count() == 0:
            return []

        top_k = min(top_k, MAX_TOP_K, collection.count())
        query_vector = self.embeddings.embed_query(query)

        # Build where filter for doc_ids
        where_filter = None
        if doc_ids:
            if len(doc_ids) == 1:
                where_filter = {"doc_id": doc_ids[0]}
            else:
                where_filter = {"doc_id": {"$in": doc_ids}}

        query_params = {
            "query_embeddings": [query_vector],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_params["where"] = where_filter

        results = collection.query(**query_params)

        chunks = []
        if results and results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                chunks.append({
                    "content": doc,
                    "doc_id": meta.get("doc_id"),
                    "filename": meta.get("filename"),
                    "chunk_index": meta.get("chunk_index"),
                })

        return chunks

    def sanitize_chunk(self, text: str) -> str:
        """Sanitize chunk content. Regex is辅助, prompt-level defense is the primary guard."""
        if len(text) > SANITIZE_MAX_LEN:
            text = text[:SANITIZE_MAX_LEN] + "..."
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
        return text

    def build_context(self, chunks: List[dict]) -> Optional[str]:
        """Build context string from retrieved chunks for prompt injection."""
        if not chunks:
            return None

        sanitized = []
        for chunk in chunks:
            clean = self.sanitize_chunk(chunk["content"])
            sanitized.append(clean)

        context = "\n---\n".join(sanitized)
        return context

    def build_references(self, chunks: List[dict]) -> List[dict]:
        """Build reference info for frontend."""
        refs = []
        for chunk in chunks:
            snippet = chunk["content"][:200]
            refs.append({
                "doc_id": chunk.get("doc_id"),
                "filename": chunk.get("filename"),
                "chunk_index": chunk.get("chunk_index"),
                "snippet": snippet,
            })
        return refs


# Global singleton
_rag_service: Optional[RagService] = None


def get_rag_service() -> RagService:
    """Get or create the global RagService instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
