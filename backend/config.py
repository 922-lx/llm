"""
项目配置文件
"""
import os

class Config:
    # ====== Flask ======
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ds-kg-llm-2026-secret')
    DEBUG = True

    # ====== MySQL ======
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '123456')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'ds_kg_db')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ====== Neo4j ======
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'neo4j123')

    # ====== LLM / RAG ======
    # 本地模型路径（LoRA微调后）
    LLM_MODEL_PATH = os.environ.get('LLM_MODEL_PATH', './models/qwen2.5-7b-ds-lora')
    # 向量嵌入模型（sentence-transformers）
    EMBED_MODEL_PATH = os.environ.get('EMBED_MODEL_PATH', 'BAAI/bge-large-zh-v1.5')
    # FAISS 索引路径
    FAISS_INDEX_PATH = os.environ.get('FAISS_INDEX_PATH', './data/faiss_index')
    # RAG 检索 top-k
    RAG_TOP_K = 5

    # ====== CORS ======
    CORS_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
