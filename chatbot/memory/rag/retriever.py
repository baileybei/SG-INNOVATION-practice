"""
医疗知识 RAG 检索器
向量存储：ChromaDB（本地持久化）
嵌入模型：paraphrase-multilingual-MiniLM-L12-v2（中英双语）
首次调用自动建索引；后续从磁盘加载，毫秒级检索。
未安装依赖时静默跳过，不影响正常对话流程。
"""
from pathlib import Path

CHROMA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "chroma_db"
COLLECTION  = "medical_knowledge"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class MedicalRetriever:
    def __init__(self):
        self._ready  = False
        self._col    = None
        self._embedder = None

    def _init(self):
        if self._ready:
            return
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            client      = chromadb.PersistentClient(path=str(CHROMA_PATH))
            self._col   = client.get_or_create_collection(COLLECTION)
            self._embedder = SentenceTransformer(EMBED_MODEL)

            if self._col.count() == 0:
                self._index_knowledge_base()

            self._ready = True
            print(f"[RAG] 检索器就绪，知识库 {self._col.count()} 个文档块")

        except ImportError:
            print("[RAG] chromadb / sentence-transformers 未安装，RAG 已跳过")
        except Exception as e:
            print(f"[RAG] 初始化失败：{e}")

    def _index_knowledge_base(self):
        from chatbot.memory.rag.loader import load_all_chunks
        chunks = load_all_chunks()
        if not chunks:
            print("[RAG] 知识库为空，跳过索引")
            return
        embeddings = self._embedder.encode(
            [c["text"] for c in chunks], show_progress_bar=False
        ).tolist()
        self._col.add(
            ids        =[c["id"]       for c in chunks],
            documents  =[c["text"]     for c in chunks],
            embeddings =embeddings,
            metadatas  =[c["metadata"] for c in chunks],
        )
        print(f"[RAG] 知识库索引完成：{len(chunks)} 个文档块")

    def retrieve(self, query: str, n: int = 3) -> str:
        """
        语义检索，返回格式化的参考资料字符串。
        未就绪或检索失败时返回空字符串。
        """
        self._init()
        if not self._ready:
            return ""
        try:
            vec     = self._embedder.encode([query], show_progress_bar=False)[0].tolist()
            results = self._col.query(query_embeddings=[vec], n_results=n)
            docs    = results["documents"][0] if results["documents"] else []
            if not docs:
                return ""
            return "\n\n".join(docs)
        except Exception as e:
            print(f"[RAG] 检索失败：{e}")
            return ""


# ── 单例 ─────────────────────────────────────────────────────────
_retriever: "MedicalRetriever | None" = None


def get_retriever() -> MedicalRetriever:
    global _retriever
    if _retriever is None:
        _retriever = MedicalRetriever()
    return _retriever
