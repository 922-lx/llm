"""
数据库初始化脚本
创建 MySQL 数据库、表，并插入示例数据
"""
import pymysql
import json
import os
from datetime import datetime


def get_connection(host='127.0.0.1', port=3306, user='root', password='root123'):
    """获取 MySQL 连接（先连接无数据库的实例）"""
    return pymysql.connect(
        host=host, port=port, user=user, password=password,
        charset='utf8mb4', autocommit=True
    )


def init_database(host='127.0.0.1', port=3306, user='root', password='root123',
                  db_name='ds_kg_db'):
    """创建数据库和表结构"""
    conn = get_connection(host, port, user, password)
    cursor = conn.cursor()

    # 创建数据库
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{db_name}`")
    print(f"[DB] 数据库 '{db_name}' 已创建/已存在")

    # 建表
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(64) UNIQUE NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
            role VARCHAR(16) DEFAULT 'student',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'
        """,
        """
        CREATE TABLE IF NOT EXISTS knowledge_points (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            course VARCHAR(64),
            category VARCHAR(64) COMMENT '概念/原理/算法/数据结构',
            description TEXT,
            difficulty INT DEFAULT 1,
            neo4j_node_id VARCHAR(64),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识点表'
        """,
        """
        CREATE TABLE IF NOT EXISTS exercises (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title TEXT NOT NULL,
            type VARCHAR(32) COMMENT '选择/填空/编程/简答',
            answer TEXT,
            analysis TEXT,
            difficulty INT DEFAULT 1,
            course VARCHAR(64),
            knowledge_point_ids JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='习题表'
        """,
        """
        CREATE TABLE IF NOT EXISTS learning_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            knowledge_point_id INT,
            exercise_id INT,
            score FLOAT,
            is_correct BOOLEAN,
            time_spent INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学习记录表'
        """,
        """
        CREATE TABLE IF NOT EXISTS qa_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            retrieved_nodes JSON,
            rating INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问答历史表'
        """,
        """
        CREATE TABLE IF NOT EXISTS raw_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            source VARCHAR(256),
            source_type VARCHAR(32),
            content LONGTEXT,
            processed BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='原始数据表'
        """,
    ]

    for sql in tables_sql:
        cursor.execute(sql)
    print("[DB] 表结构创建完成")

    # 插入示例数据
    _insert_sample_data(cursor)

    cursor.close()
    conn.close()
    print("[DB] 初始化完成！")


def _insert_sample_data(cursor):
    """插入示例知识点、习题、用户"""

    # ── 示例知识点 ──
    kp_data = [
        ('数组', '数据结构', 'DS', '一种线性数据结构，用连续的存储空间存储一组相同类型的数据元素，支持通过下标随机访问。', 1),
        ('链表', '数据结构', 'DS', '一种物理上非连续、非顺序的存储结构，通过指针将各数据元素串联起来。', 2),
        ('栈', '数据结构', 'DS', '一种后进先出（LIFO）的线性表，只允许在表尾（栈顶）进行插入和删除操作。', 1),
        ('队列', '数据结构', 'DS', '一种先进先出（FIFO）的线性表，只允许在表尾插入、表头删除。', 1),
        ('二叉树', '数据结构', 'DS', '每个节点最多有两个子节点的树形结构，分为左子树和右子树。', 2),
        ('二叉搜索树', '数据结构', 'DS', '左子树所有节点值小于根节点、右子树所有节点值大于根节点的二叉树。', 3),
        ('AVL树', '数据结构', 'DS', '一种自平衡二叉搜索树，任意节点的左右子树高度差不超过1。', 4),
        ('红黑树', '数据结构', 'DS', '一种近似平衡的二叉搜索树，通过着色规则保持平衡。', 4),
        ('堆', '数据结构', 'DS', '一种特殊的完全二叉树，分为最大堆和最小堆。', 3),
        ('图', '数据结构', 'DS', '由顶点集合和边集合组成的非线性数据结构。', 3),
        ('哈希表', '数据结构', 'DS', '根据关键字直接访问数据的数据结构，通过哈希函数映射到存储位置。', 3),
        ('冒泡排序', '数据结构', 'ALGO', '通过重复遍历待排序序列，依次比较相邻元素并交换的排序算法，时间复杂度O(n²)。', 1),
        ('快速排序', '数据结构', 'ALGO', '选取基准元素，将序列分为两部分，递归排序的分治算法，平均时间复杂度O(nlogn)。', 3),
        ('归并排序', '数据结构', 'ALGO', '将序列递归拆分为子序列，排序后再合并的稳定排序算法，时间复杂度O(nlogn)。', 3),
        ('深度优先搜索', '数据结构', 'ALGO', '沿着图的深度方向尽可能深地搜索，使用栈或递归实现。', 2),
        ('广度优先搜索', '数据结构', 'ALGO', '从起始节点出发，依次访问其邻接节点，使用队列实现。', 2),
        ('动态规划', '数据结构', 'METHOD', '将复杂问题分解为重叠子问题，通过记忆化避免重复计算的算法设计方法。', 4),
        ('贪心算法', '数据结构', 'METHOD', '每步选择当前最优解，期望全局最优的算法设计方法。', 3),
        ('递归', '数据结构', 'METHOD', '函数直接或间接调用自身的编程方法，常用于树和图的遍历。', 2),
        ('分治算法', '数据结构', 'METHOD', '将问题分解为独立子问题，分别解决后合并结果的算法设计方法。', 3),
        ('时间复杂度', '数据结构', 'CONCEPT', '衡量算法执行时间随输入规模增长的变化趋势。', 1),
        ('空间复杂度', '数据结构', 'CONCEPT', '衡量算法执行过程中所需额外空间随输入规模增长的变化趋势。', 1),
        ('最优子结构', '数据结构', 'PRINCIPLE', '问题的最优解包含其子问题的最优解，是动态规划的基本要素。', 3),
    ]

    cursor.execute("SELECT COUNT(*) FROM knowledge_points")
    if cursor.fetchone()[0] == 0:
        for kp in kp_data:
            cursor.execute(
                "INSERT INTO knowledge_points (name, course, category, description, difficulty) VALUES (%s,%s,%s,%s,%s)",
                kp
            )
        print(f"[DB] 插入 {len(kp_data)} 条示例知识点")

    # ── 示例习题 ──
    exercises = [
        ('数组中第k大的元素是什么？', '编程', '使用快速选择算法或堆排序找到第k大的元素。', '利用快速排序的分区思想，每次分区后判断目标位置所在区间。', 3, '数据结构', [1]),
        ('实现一个栈的两个基本操作push和pop。', '编程', 'push将元素压入栈顶，pop弹出栈顶元素。', '注意栈空判断和边界条件。', 1, '数据结构', [3]),
        ('快速排序的平均时间复杂度是？', '选择', 'O(nlogn)', '快速排序的分区过程平均将数组分为等大的两部分，递归深度为logn。', 2, '数据结构', [12]),
        ('二叉搜索树的中序遍历结果有什么特点？', '简答', '中序遍历结果是一个递增序列', 'BST的定义保证了左子树 < 根 < 右子树，中序遍历依次访问左、根、右。', 2, '数据结构', [5]),
        ('使用哈希表实现两数之和。', '编程', '遍历数组，用哈希表存储已遍历的值和下标，查找target-当前值。', '时间复杂度O(n)，空间复杂度O(n)。', 3, '数据结构', [1, 11]),
        ('什么是动态规划？与分治法有什么区别？', '简答', '动态规划将问题分解为重叠子问题，通过记忆化避免重复计算。分治法的子问题是独立的。', '重叠子问题+最优子结构是动态规划的标志。', 3, '数据结构', [16, 19]),
        ('AVL树和红黑树有什么区别？', '简答', 'AVL严格平衡（高度差<=1），查询效率高；红黑树近似平衡，插入删除效率高。', 'AVL适合读多写少场景，红黑树适合读写均衡场景。', 4, '数据结构', [6, 7]),
        ('实现队列的入队和出队操作（使用链表）。', '编程', '链表头为队头，尾为队尾。入队在尾部插入，出队在头部删除。', '需维护头尾指针。', 2, '数据结构', [4]),
        ('图的BFS和DFS分别使用什么数据结构？', '选择', 'BFS使用队列，DFS使用栈（或递归）', 'BFS逐层遍历用队列，DFS深入探索用栈。', 2, '数据结构', [9, 14, 15]),
        ('归并排序是稳定的排序算法吗？为什么？', '简答', '是的。归并排序在合并时，相等元素保持原有顺序。', '合并时左侧元素优先，遇到相等元素先放左侧。', 3, '数据结构', [13]),
    ]

    cursor.execute("SELECT COUNT(*) FROM exercises")
    if cursor.fetchone()[0] == 0:
        for ex in exercises:
            title, typ, answer, analysis, difficulty, course, kp_ids = ex
            cursor.execute(
                "INSERT INTO exercises (title, type, answer, analysis, difficulty, course, knowledge_point_ids) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (title, typ, answer, analysis, difficulty, course, json.dumps(kp_ids))
            )
        print(f"[DB] 插入 {len(exercises)} 道示例习题")

    # ── 示例用户 ──
    import hashlib
    demo_users = [
        ('student1', hashlib.sha256('123456'.encode()).hexdigest(), 'student'),
        ('teacher1', hashlib.sha256('123456'.encode()).hexdigest(), 'teacher'),
        ('admin',    hashlib.sha256('admin123'.encode()).hexdigest(), 'admin'),
    ]

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        for u in demo_users:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)", u
            )
        print(f"[DB] 插入 {len(demo_users)} 个示例用户")


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=3306)
    p.add_argument('--user', default='root')
    p.add_argument('--pwd', default='root123')
    p.add_argument('--db', default='ds_kg_db')
    args = p.parse_args()
    init_database(args.host, args.port, args.user, args.pwd, args.db)
