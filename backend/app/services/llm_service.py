"""
LLM 推理服务
- 优先使用本地 Ollama（Qwen2.5:7b）
- 备用：OpenAI 兼容接口
- 最终降级：基于知识库检索结果的简单回答
"""
import os
import re
import json
import urllib.request
from flask import current_app


# Ollama 本地服务地址（固定，无需配置）
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"


def _simple_answer(prompt: str) -> str:
    """最终降级：从 prompt 中提取参考资料，生成简单回答"""
    ref_match = re.search(r'【参考资料】\s*(.*?)\s*【学生问题】', prompt, re.DOTALL)
    q_match = re.search(r'【学生问题】\s*(.*?)\s*$', prompt, re.DOTALL)
    question = q_match.group(1).strip() if q_match else ""
    refs = ref_match.group(1).strip() if ref_match else ""

    if refs:
        return f"根据参考资料，关于「{question}」的回答：\n\n{refs}"
    else:
        return f"关于「{question}」的问题：当前知识库中暂无相关参考资料，请先通过知识图谱管理添加知识点。"


def _call_ollama(prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """
    调用本地 Ollama API（OpenAI 兼容格式）
    返回生成的文本，失败时抛出异常
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "你是数据结构课程的专业助教，请准确、简洁地回答学生的问题。"},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode("utf-8"))
    return result["message"]["content"]


def _check_ollama_available() -> bool:
    """检查 Ollama 服务是否可用"""
    try:
        resp = urllib.request.urlopen(OLLAMA_BASE_URL, timeout=3)
        return resp.status == 200
    except Exception:
        return False


class LLMService:
    """大语言模型推理封装"""

    def __init__(self):
        self._ollama_available = None  # None=未检查，True/False=检查结果

    def _ensure_ollama_checked(self):
        """懒检查 Ollama 是否可用（只检查一次）"""
        if self._ollama_available is None:
            self._ollama_available = _check_ollama_available()
            if self._ollama_available:
                try:
                    current_app.logger.info(f"[LLM] Ollama 服务可用，使用模型: {OLLAMA_MODEL}")
                except Exception:
                    pass
            else:
                try:
                    current_app.logger.warning("[LLM] Ollama 服务不可用，将降级处理")
                except Exception:
                    pass

    def generate(self, prompt: str, max_new_tokens: int = 1024,
                 temperature: float = 0.7, top_p: float = 0.9) -> str:
        """
        生成回答
        优先级：Ollama 本地模型 > OpenAI 兼容 API > 降级简单回答
        """
        self._ensure_ollama_checked()

        # 优先使用 Ollama
        if self._ollama_available:
            try:
                answer = _call_ollama(prompt, max_tokens=max_new_tokens, temperature=temperature)
                try:
                    current_app.logger.info("[LLM] Ollama 推理成功")
                except Exception:
                    pass
                return answer
            except Exception as e:
                try:
                    current_app.logger.error(f"[LLM] Ollama 推理失败: {e}，回退到备用方案")
                except Exception:
                    pass
                self._ollama_available = False  # 标记本次不可用

        # 备用：OpenAI 兼容 API
        api_base = os.environ.get('OPENAI_API_BASE', '')
        if api_base:
            try:
                import openai
                client = openai.OpenAI(
                    base_url=api_base,
                    api_key=os.environ.get('OPENAI_API_KEY', 'no-key'),
                )
                response = client.chat.completions.create(
                    model=os.environ.get('OPENAI_MODEL_NAME', 'qwen2.5:7b'),
                    messages=[
                        {"role": "system", "content": "你是数据结构课程的专业助教，请准确回答学生的问题。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                try:
                    current_app.logger.error(f"[LLM] OpenAI API 调用失败: {e}")
                except Exception:
                    pass

        # 最终降级
        return _simple_answer(prompt)


llm_service = LLMService()
