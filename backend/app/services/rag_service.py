"""
RAG 问答引擎
- 语义检索：FAISS + sentence-transformers
- 知识图谱辅助检索
- 生成：调用本地 LLM（Qwen2.5-7B-Instruct + LoRA）
"""
import os
import json
import numpy as np
from typing import List, Dict, Tuple
from flask import current_app


class RAGService:
    """检索增强生成服务"""

    def __init__(self):
        self._embed_model = None
        self._faiss_index = None
        self._doc_chunks = []   # 文本块列表，与 FAISS 索引对齐
        self._llm_service = None

    # ------------------------------------------------------------------ #
    #  懒加载
    # ------------------------------------------------------------------ #

    def _get_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            model_path = current_app.config.get('EMBED_MODEL_PATH', 'BAAI/bge-large-zh-v1.5')
            self._embed_model = SentenceTransformer(model_path)
        return self._embed_model

    def _get_faiss_index(self):
        if self._faiss_index is None:
            import faiss
            index_path = current_app.config.get('FAISS_INDEX_PATH', './data/faiss_index')
            idx_file = os.path.join(index_path, 'index.bin')
            chunk_file = os.path.join(index_path, 'chunks.json')
            if os.path.exists(idx_file):
                self._faiss_index = faiss.read_index(idx_file)
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    self._doc_chunks = json.load(f)
            else:
                current_app.logger.warning("FAISS 索引文件不存在，请先运行 build_index()")
        return self._faiss_index

    def _get_llm(self):
        if self._llm_service is None:
            from app.services.llm_service import LLMService
            self._llm_service = LLMService()
        return self._llm_service

    # ------------------------------------------------------------------ #
    #  索引构建（离线调用一次）
    # ------------------------------------------------------------------ #

    def build_index(self, text_chunks: List[str], save_dir: str = './data/faiss_index'):
        """
        对文本块建立 FAISS 向量索引
        text_chunks: 知识文本块（每条约 200-500 字）
        """
        import faiss
        os.makedirs(save_dir, exist_ok=True)
        model = self._get_embed_model()
        print(f"[RAG] 正在编码 {len(text_chunks)} 条文本...")
        embeddings = model.encode(text_chunks, batch_size=64, show_progress_bar=True,
                                  normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype='float32')
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)   # 内积 = cosine（已归一化）
        index.add(embeddings)
        faiss.write_index(index, os.path.join(save_dir, 'index.bin'))
        with open(os.path.join(save_dir, 'chunks.json'), 'w', encoding='utf-8') as f:
            json.dump(text_chunks, f, ensure_ascii=False, indent=2)
        self._faiss_index = index
        self._doc_chunks = text_chunks
        print(f"[RAG] 索引构建完成，共 {index.ntotal} 条向量")

    # ------------------------------------------------------------------ #
    #  检索
    # ------------------------------------------------------------------ #

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        语义检索：返回 top_k 条最相关文本块
        """
        if top_k is None:
            top_k = current_app.config.get('RAG_TOP_K', 5)

        index = self._get_faiss_index()
        if index is None:
            return []

        model = self._get_embed_model()
        q_vec = model.encode([query], normalize_embeddings=True).astype('float32')
        scores, idx_list = index.search(q_vec, top_k)

        results = []
        for score, i in zip(scores[0], idx_list[0]):
            if i < len(self._doc_chunks):
                results.append({
                    'text': self._doc_chunks[i],
                    'score': float(score),
                    'chunk_id': int(i),
                })
        return results

    def retrieve_from_kg(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        从知识图谱检索相关节点（关键词匹配 + 语义扩展）
        降级：如果 Neo4j 不可用，从 MySQL 知识点表中模糊匹配
        """
        try:
            from app.services.kg_service import kg_service
            nodes = kg_service.search_nodes(query, limit=top_k)
            results = []
            for n in nodes:
                text = f"知识点：{n.get('name', '')}\n类别：{n.get('category', '')}\n描述：{n.get('description', '')}"
                results.append({'text': text, 'score': 1.0, 'node': n})
            return results
        except Exception:
            # Neo4j 不可用，降级到 MySQL
            return self._retrieve_from_mysql(query, top_k)

    def _retrieve_from_mysql(self, query: str, top_k: int = 5) -> List[Dict]:
        """从 MySQL 知识点表模糊匹配（降级方案）"""
        from app.models.models import KnowledgePoint
        results = []
        kps = KnowledgePoint.query.filter(
            KnowledgePoint.name.contains(query) |
            KnowledgePoint.description.contains(query) |
            KnowledgePoint.category.contains(query)
        ).limit(top_k).all()
        for kp in kps:
            text = f"知识点：{kp.name}\n类别：{kp.category}\n描述：{kp.description}"
            results.append({'text': text, 'score': 1.0, 'node': {'name': kp.name, 'category': kp.category}})
        if not kps:
            # 返回一些通用的知识点作为上下文
            kps = KnowledgePoint.query.limit(top_k).all()
            for kp in kps:
                text = f"知识点：{kp.name}\n类别：{kp.category}\n描述：{kp.description}"
                results.append({'text': text, 'score': 0.5, 'node': {'name': kp.name, 'category': kp.category}})
        return results

    # ------------------------------------------------------------------ #
    #  问答
    # ------------------------------------------------------------------ #

    def answer(self, question: str, user_id: int = None) -> Dict:
        """
        完整 RAG 问答流程：
        1. 语义检索文档块
        2. 知识图谱检索相关节点
        3. 拼装 Prompt
        4. LLM 生成回答
        """
        # Step 1: 向量检索
        doc_results = self.retrieve(question, top_k=4)
        # Step 2: 图谱检索
        kg_results = self.retrieve_from_kg(question, top_k=3)

        # Step 3: 构建上下文
        context_parts = []
        for r in doc_results:
            context_parts.append(r['text'])
        for r in kg_results:
            context_parts.append(r['text'])

        context = "\n\n".join(context_parts) if context_parts else "暂无相关上下文。"

        # Step 4: 构建 Prompt
        prompt = self._build_prompt(question, context)

        # Step 5: LLM 推理
        llm = self._get_llm()
        answer_text = llm.generate(prompt)

        # 收集检索到的知识点名称
        retrieved_nodes = [r.get('node', {}).get('name', '') for r in kg_results if 'node' in r]

        # 记录问答历史
        if user_id:
            self._save_qa_history(user_id, question, answer_text, retrieved_nodes)

        return {
            'question': question,
            'answer': answer_text,
            'retrieved_context': context_parts,
            'retrieved_nodes': retrieved_nodes,
        }

    @staticmethod
    def _build_prompt(question: str, context: str) -> str:
        return f"""你是一位专业的数据结构课程助教，请根据以下参考资料回答学生提问。
如果参考资料中没有相关信息，请基于你的知识给出准确回答，并注明"基于通用知识"。
回答要求：简明扼要，重点突出，必要时给出示例或代码。

【参考资料】
{context}

【学生问题】
{question}

【回答】"""

    @staticmethod
    def _save_qa_history(user_id: int, question: str, answer: str, nodes: List[str]):
        try:
            from app.models.models import QAHistory
            from app import db
            record = QAHistory(
                user_id=user_id,
                question=question,
                answer=answer,
                retrieved_nodes=nodes
            )
            db.session.add(record)
            db.session.commit()
        except Exception as e:
            print(f"[RAG] 保存问答历史失败: {e}")


rag_service = RAGService()
