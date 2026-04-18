# 📖 从零开始搭建 —— 超详细步骤指南

> 本文档教你从一台全新的 Windows 电脑开始，一步步把项目跑起来。

---

## 第一步：安装必需软件

### 1.1 安装 Python 3.10

1. 打开浏览器，访问：https://www.python.org/downloads/
2. 下载 **Python 3.10.x**（推荐 3.10.11）
3. 运行安装程序，**一定要勾选 "Add Python to PATH"**
4. 安装完成后，打开 PowerShell 验证：

```powershell
python --version
```
看到 `Python 3.10.x` 就对了。

### 1.2 安装 Node.js

1. 访问：https://nodejs.org/
2. 下载 **LTS 版本**（18.x 或 20.x）
3. 运行安装，一路 Next
4. 验证：

```powershell
node --version
npm --version
```

### 1.3 安装 MySQL 8.0

1. 访问：https://dev.mysql.com/downloads/installer/
2. 下载 **mysql-installer-community**（较大的那个）
3. 运行安装，选择 **Server only**
4. 配置时设置：
   - **端口**：`3306`（默认）
   - **Root 密码**：设为 `root123`（和项目配置一致）
   - 勾选 **Configure MySQL Server as a Windows Service**
5. 安装完成后验证（在 PowerShell 中）：

```powershell
mysql -u root -proot123 -e "SELECT VERSION();"
```

### 1.4 安装 Neo4j

1. 访问：https://neo4j.com/download-center/
2. 下载 **Neo4j Desktop**（桌面版，有图形界面）
3. 安装后打开，创建一个新项目：
   - **Project Name**：`DS-KG`
   - **Database Name**：`neo4j`
   - **Password**：设为 `neo4j123`（和项目配置一致）
4. 点击 **Start** 启动数据库
5. 浏览器打开 http://localhost:7474 能看到 Neo4j 浏览器界面就对了

---

## 第二步：准备项目代码

### 2.1 找到项目目录

项目代码在：

```
C:\Users\Administrator\WorkBuddy\20260402224226\ds-kg-llm-system\
```

### 2.2（可选）复制到桌面方便操作

```powershell
Copy-Item -Recurse "C:\Users\Administrator\WorkBuddy\20260402224226\ds-kg-llm-system" "C:\Users\Administrator\Desktop\ds-kg-llm-system"
```

以后就在 `C:\Users\Administrator\Desktop\ds-kg-llm-system` 里操作。

---

## 第三步：配置后端

### 3.1 创建 Python 虚拟环境

打开 PowerShell，进入后端目录：

```powershell
cd C:\Users\Administrator\Desktop\ds-kg-llm-system\backend
python -m venv venv
```

### 3.2 激活虚拟环境

```powershell
.\venv\Scripts\Activate.ps1
```

> 如果报错说"无法加载，因为在此系统上禁止运行脚本"，先执行：
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
> 然后再激活。

激活后命令行前面会多一个 `(venv)`。

### 3.3 安装 Python 依赖

```powershell
pip install -r requirements.txt
```

等几分钟，看到 "Successfully installed..." 就好了。

### 3.4 修改数据库密码（如果和默认不同）

用记事本打开 `backend\config.py`，检查这几行：

```python
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root123')    # ← 你的 MySQL 密码
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'neo4j123')   # ← 你的 Neo4j 密码
```

如果你的密码不是 `root123` / `neo4j123`，直接把引号里的值改成你的密码。

---

## 第四步：初始化数据库

### 4.1 初始化 MySQL

确保虚拟环境已激活，在项目根目录执行：

```powershell
cd C:\Users\Administrator\Desktop\ds-kg-llm-system
python scripts\init_db.py --pwd root123
```

> `--pwd` 后面换成你的 MySQL 密码。

看到以下输出就成功了：
```
[DB] 数据库 'ds_kg_db' 已创建/已存在
[DB] 表结构创建完成
[DB] 插入 23 条示例知识点
[DB] 插入 10 道示例习题
[DB] 插入 3 个示例用户
[DB] 初始化完成！
```

### 4.2 验证 MySQL

```powershell
mysql -u root -proot123 -e "USE ds_kg_db; SHOW TABLES;"
```

应该看到 6 张表：`users`, `knowledge_points`, `exercises`, `learning_records`, `qa_history`, `raw_data`。

### 4.3 构建 Neo4j 知识图谱

```powershell
cd C:\Users\Administrator\Desktop\ds-kg-llm-system
python scripts\kg_builder.py --sample
```

看到输出类似 "已创建 X 个节点, Y 条关系" 就成功了。

验证：打开浏览器 http://localhost:7474，在查询框输入：

```cypher
MATCH (n) RETURN n LIMIT 25
```

点击运行，能看到数据结构相关的节点图就对了！

---

## 第五步：启动后端

```powershell
cd C:\Users\Administrator\Desktop\ds-kg-llm-system\backend
.\venv\Scripts\Activate.ps1
python run.py
```

看到：
```
 * Running on http://127.0.0.1:5000
```

说明后端启动成功！**这个窗口不要关**。

测试一下：浏览器打开 http://localhost:5000/api/health

应该看到：`{"status":"ok","message":"数据结构智能问答系统运行中"}`

---

## 第六步：启动前端

### 6.1 打开一个新的 PowerShell 窗口

（后端窗口不要关！）

### 6.2 安装前端依赖

```powershell
cd C:\Users\Administrator\Desktop\ds-kg-llm-system\frontend
npm install
```

等一两分钟，看到 "added xxx packages" 就好了。

### 6.3 启动前端开发服务器

```powershell
npm run dev
```

看到：
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

说明前端启动成功！

### 6.4 打开浏览器访问

浏览器打开：**http://localhost:5173**

你应该能看到登录页面！

### 6.5 登录测试

| 用户名 | 密码 | 角色 |
|--------|------|------|
| **student1** | **123456** | 学生 |
| teacher1 | 123456 | 教师 |
| admin | admin123 | 管理员 |

输入 `student1` / `123456`，登录后可以看到：
- 📊 **知识图谱** —— 可视化浏览数据结构知识点
- 💬 **智能问答** —— 输入问题获取 AI 回答
- 📝 **习题练习** —— 做题和查看解析
- 🛤️ **学习路径** —— 推荐学习顺序

---

## 第七步：（可选）构建向量索引让 AI 问答更智能

默认情况下，问答模块会使用简单的模板回复。要启用 RAG（检索增强生成），需要构建向量索引。

### 7.1 构建索引

在**后端窗口**（先 Ctrl+C 停止后端），执行：

```powershell
cd C:\Users\Administrator\Desktop\ds-kg-llm-system\backend
.\venv\Scripts\Activate.ps1
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.services.rag_service import rag_service
    docs = [
        '数组是一种线性数据结构，用连续的存储空间存储相同类型的数据元素。',
        '链表是通过指针将各数据元素串联起来的非连续存储结构。',
        '栈是后进先出LIFO的线性表，只允许在栈顶进行插入和删除。',
        '队列是先进先出FIFO的线性表，只允许在队尾插入、队头删除。',
        '二叉树每个节点最多有两个子节点，分为左子树和右子树。',
        '快速排序选取基准元素分区，递归排序，平均时间复杂度O(nlogn)。',
        '动态规划将问题分解为重叠子问题，通过记忆化避免重复计算。',
        '深度优先搜索沿着深度方向尽可能深地搜索，使用栈实现。',
        '广度优先搜索从起始节点逐层访问，使用队列实现。',
        '哈希表通过哈希函数将关键字映射到存储位置，支持O(1)查找。',
    ]
    rag_service.build_index(docs)
    print('向量索引构建完成！')
"
```

### 7.2 重新启动后端

```powershell
python run.py
```

现在去前端问答页面提问，比如输入"什么是快速排序？"，系统会从向量库中检索相关知识再生成回答。

---

## 常见问题排查

### ❌ `pip install` 报错？

尝试升级 pip：
```powershell
python -m pip install --upgrade pip
```

### ❌ MySQL 连接失败？

检查：
1. MySQL 服务是否在运行：`net start mysql`
2. 密码是否正确
3. 端口是否是 3306

### ❌ Neo4j 连接失败？

检查：
1. Neo4j Desktop 里数据库是否已点 Start
2. 密码是否是 `neo4j123`
3. 浏览器能否打开 http://localhost:7474

### ❌ 前端页面空白？

1. 检查后端是否在运行
2. 打开浏览器 F12 控制台看报错信息
3. 确认前端 `npm run dev` 没有报错

### ❌ `Set-ExecutionPolicy` 报错？

以**管理员身份**打开 PowerShell 再执行：
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### ❌ 没有显卡，能跑 AI 模型吗？

**可以！** 项目默认使用 CPU 模式。NER/RE 模型在 CPU 上也能跑（慢一些）。
LLM 问答会回退到模板回复，或者你可以用 Ollama 跑本地模型。

如果想用 Ollama：
```powershell
# 1. 安装 Ollama: https://ollama.com
# 2. 下载模型
ollama pull qwen2.5:7b
# 3. 修改 config.py 中的 LLM_MODEL_PATH 为 'ollama://qwen2.5:7b'
```

---

## 📌 每次开发需要做的事

每次重新打开电脑，只需要：

```powershell
# 终端1：启动后端
cd C:\Users\Administrator\Desktop\ds-kg-llm-system\backend
.\venv\Scripts\Activate.ps1
python run.py

# 终端2：启动前端（新开窗口）
cd C:\Users\Administrator\Desktop\ds-kg-llm-system\frontend
npm run dev
```

然后浏览器打开 http://localhost:5173 就行了！

---

## 📌 项目功能说明

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录页 | `/login` | 用户登录注册 |
| 智能问答 | `/chat` | 和 AI 对话学习数据结构 |
| 知识图谱 | `/kg` | 可视化浏览知识点关系 |
| 习题练习 | `/exercises` | 做题、查看解析 |
| 学习路径 | `/path` | 推荐学习顺序 |
| 个人中心 | `/profile` | 查看学习统计 |
