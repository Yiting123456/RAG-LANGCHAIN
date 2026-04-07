# tools/rag.py
import json
import numpy as np
import ollama
from typing import List, Dict, Any


# ============================================================
# Embedding（Ollama）
# ============================================================
def embed_text(text: str) -> List[float]:
    resp = ollama.embeddings(
        model="qwen3-embedding:8b",
        prompt=text
    )
    return resp["embedding"]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    return float(np.dot(np.array(v1), np.array(v2)))


# ============================================================
# ✅ main.py 需要的接口 1
# ============================================================
def build_qa_index(path: str) -> List[Dict[str, Any]]:
    """
    构建 QA 向量索引
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    vectors = []
    for item in data:
        text = f"""
【问题】{item.get("question", "")}
【答案】{item.get("answer", "")}
"""
        vectors.append({
            "vector": embed_text(text),
            "item": item
        })

    return vectors


# ============================================================
# ✅ main.py 需要的接口 2
# ============================================================
def build_process_index(path: str) -> List[Dict[str, Any]]:
    """
    构建 工艺 / 过程 向量索引
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    vectors = []
    for chunk in data:
        text = f"""
【工艺阶段】{chunk.get("process_stage", "")}
【设备】{",".join(chunk.get("equipment", []))}
【说明】{chunk.get("content", "")}
"""
        vectors.append({
            "vector": embed_text(text),
            "item": chunk
        })

    return vectors


# ============================================================
# ✅ main.py 需要的接口 3
# ============================================================
def rag_search(
    query: str,
    qa_vectors: List[Dict[str, Any]],
    process_vectors: List[Dict[str, Any]],
    top_k_qa: int = 1,
    top_k_process: int = 1
) -> Dict[str, Any]:
    """
    RAG 检索
    """
    query_vec = embed_text(query)

    qa_scored = sorted(
        qa_vectors,
        key=lambda x: cosine_similarity(query_vec, x["vector"]),
        reverse=True
    )[:top_k_qa]

    process_scored = sorted(
        process_vectors,
        key=lambda x: cosine_similarity(query_vec, x["vector"]),
        reverse=True
    )[:top_k_process]

    return {
        "qa": [x["item"] for x in qa_scored],
        "process": [x["item"] for x in process_scored]
    }