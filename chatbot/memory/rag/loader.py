"""
知识库文档加载器
将 knowledge/ 目录下的 .txt 文件切分成段落级 chunk
"""
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def load_all_chunks() -> list[dict]:
    """
    加载所有知识库文档，按空行分段，过滤过短内容。
    返回 [{"id": str, "text": str, "metadata": dict}]
    """
    chunks   = []
    chunk_id = 0

    for doc_file in sorted(KNOWLEDGE_DIR.glob("*.txt")):
        text       = doc_file.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 40]
        for para in paragraphs:
            chunks.append({
                "id":       f"{doc_file.stem}_{chunk_id}",
                "text":     para,
                "metadata": {"source": doc_file.stem},
            })
            chunk_id += 1

    return chunks
