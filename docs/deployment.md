# 部署与运行指南

## 一、环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.9+ |
| Node.js | 18+ |
| MySQL | 8.0+ |
| Neo4j | 5.x |
| CUDA（可选） | 11.8+ (GPU训练) |
| GPU显存（可选） | ≥16GB (Qwen2.5-7B) |

## 二、后端部署

### 1. 创建 Python 虚拟环境

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

编辑 `backend/config.py`，修改 MySQL 和 Neo4j 连接信息：

```python
MYSQL_HOST = '127.0.0.1'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'

NEO4J_URI = 'bolt://localhost:7687'
NEO4J_USER = 'neo4j'
NEO4J_PASSWORD = 'your_password'
```

### 4. 初始化数据库

```bash
cd scripts
python init_db.py --pwd your_mysql_password
```

### 5. 构建知识图谱（Neo4j）

```bash
# 使用内置示例数据
python kg_builder.py --sample

# 或从 JSON 文件导入
python kg_builder.py --triples ../data/kg_triples.json
```

### 6. 构建 FAISS 向量索引

```bash
cd backend
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.services.rag_service import rag_service
    # 从 Neo4j 获取知识点描述构建索引
    rag_service.build_index(['二叉树是一种重要的树形数据结构，每个节点最多有两个子节点。', ...])
"
```

或启动后通过 API 构建（需要先启动 Flask）：

```bash
curl -X POST http://localhost:5000/api/qa/build-index
```

### 7. 启动后端

```bash
cd backend
python run.py
# 服务运行在 http://localhost:5000
```

## 三、前端部署

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发模式

```bash
npm run dev
# 运行在 http://localhost:5173，自动代理到后端 5000 端口
```

### 3. 生产构建

```bash
npm run build
# 产物在 dist/ 目录，使用 Nginx 部署
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 四、模型训练（可选）

### 1. NER 实体抽取模型训练

```bash
cd scripts
# 准备标注数据后
python ner_model.py --train ../data/processed/ner_train.jsonl \
                    --dev ../data/processed/ner_dev.jsonl \
                    --save ../models/ner \
                    --epochs 10
```

### 2. RE 关系抽取模型训练

```bash
python re_model.py --train ../data/processed/re_train.jsonl \
                   --dev ../data/processed/re_dev.jsonl \
                   --save ../models/re \
                   --epochs 10
```

### 3. LLM LoRA 微调

```bash
# 需要安装 transformers, peft, trl, bitsandbytes
python lora_finetune.py train \
    --data ../data/processed/qa_train.jsonl \
    --output ../models/qwen2.5-7b-ds-lora \
    --base Qwen/Qwen2.5-7B-Instruct \
    --epochs 3

# 测试推理
python lora_finetune.py test \
    --lora ../models/qwen2.5-7b-ds-lora \
    --question "什么是快速排序？"
```

## 五、数据爬取

```bash
cd scripts
# 爬取百度百科词条
python data_crawl.py --mode crawl

# 数据清洗分块（供 RAG 使用）
python data_crawl.py --mode preprocess

# 生成 NER 训练数据（半自动标注）
python data_crawl.py --mode ner
```

## 六、测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| student1 | 123456 | 学生 |
| teacher1 | 123456 | 教师 |
| admin | admin123 | 管理员 |

## 七、常见问题

### Q: 前端无法连接后端？
检查后端是否在 5000 端口运行，Vite 代理配置是否正确。

### Q: Neo4j 连接失败？
确认 Neo4j 服务已启动，默认端口 7687。可通过 `http://localhost:7474` 访问 Neo4j Browser。

### Q: 没有 GPU 能运行吗？
可以。NER 和 RE 模型可用 CPU 训练（较慢）。LLM 推理会自动回退到 API 模式，需部署 vLLM/Ollama 等推理服务。

### Q: 如何添加更多知识点？
通过 API 接口 `/api/kg/node` 和 `/api/kg/relation` 添加，或编辑 `data/kg_triples.json` 后重新导入。
