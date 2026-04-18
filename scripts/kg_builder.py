"""
知识图谱构建脚本
- 读取 NER 抽取的实体 + RE 抽取的关系三元组
- 导入 Neo4j 图数据库
- 支持全量导入和增量更新
"""
import json
import os
from neo4j import GraphDatabase
from typing import List, Dict


class KnowledgeGraphBuilder:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    def close(self):
        self.driver.close()

    # ------------------------------------------------------------------ #
    #  单条操作
    # ------------------------------------------------------------------ #

    def create_knowledge_node(self, name, category, course,
                              description='', difficulty=1):
        """创建知识点节点"""
        with self.driver.session() as s:
            s.run(
                """
                MERGE (n:KnowledgePoint {name: $name})
                ON CREATE SET n.category = $category,
                              n.course = $course,
                              n.description = $description,
                              n.difficulty = $difficulty,
                              n.created = datetime()
                ON MATCH SET n.category = $category,
                            n.course = $course,
                            n.description = coalesce($description, n.description),
                            n.difficulty = $difficulty
                """,
                name=name, category=category, course=course,
                description=description, difficulty=difficulty,
            )
        print(f"  [节点] {name} ({category})")

    def create_relation(self, head, relation, tail, props=None):
        """创建关系"""
        with self.driver.session() as s:
            query = f"""
                MATCH (a:KnowledgePoint {{name: $head}})
                MATCH (b:KnowledgePoint {{name: $tail}})
                MERGE (a)-[r:{relation}]->(b)
            """
            if props:
                query += " SET r += $props"
            s.run(query, head=head, tail=tail, props=props)
        print(f"  [关系] {head} -[{relation}]-> {tail}")

    # ------------------------------------------------------------------ #
    #  批量导入
    # ------------------------------------------------------------------ #

    def import_from_triples(self, triples_path: str, course: str = '数据结构'):
        """
        从三元组 JSON 文件导入
        格式：[
          {"head": "链表", "head_type": "DS", "relation": "RELATED",
           "tail": "数组", "tail_type": "DS"},
          ...
        ]
        """
        with open(triples_path, 'r', encoding='utf-8') as f:
            triples = json.load(f)

        print(f"[KG] 开始导入 {len(triples)} 条三元组...")

        nodes_set = set()
        for t in triples:
            nodes_set.add((t['head'], t.get('head_type', '概念')))
            nodes_set.add((t['tail'], t.get('tail_type', '概念')))

        # 先创建所有节点
        print(f"[KG] 创建 {len(nodes_set)} 个节点...")
        for name, cat in nodes_set:
            self.create_knowledge_node(name=name, category=cat, course=course)

        # 再创建关系
        print(f"[KG] 创建 {len(triples)} 条关系...")
        for t in triples:
            self.create_relation(
                head=t['head'],
                relation=t['relation'],
                tail=t['tail'],
            )

        print("[KG] 导入完成！")

    def import_from_ner_re_results(
        self,
        ner_path: str,
        re_path: str,
        course: str = '数据结构',
    ):
        """
        从 NER 抽取结果和 RE 抽取结果构建图谱
        NER 格式: [{"text": "栈是一种...", "entities": [{"text":"栈","type":"DS","start":0,"end":1}]}, ...]
        RE 格式:  [{"text":"...", "e1":"栈", "e2":"队列", "relation":"RELATED"}, ...]
        """
        # 加载 NER 实体
        with open(ner_path, 'r', encoding='utf-8') as f:
            ner_data = json.load(f)

        entity_set = {}
        for doc in ner_data:
            for ent in doc.get('entities', []):
                name = ent['text'].strip()
                if name and name not in entity_set:
                    entity_set[name] = ent.get('type', 'CONCEPT')

        print(f"[KG] NER 抽取到 {len(entity_set)} 个不同实体")
        for name, cat in entity_set.items():
            self.create_knowledge_node(name=name, category=cat, course=course)

        # 加载 RE 关系
        with open(re_path, 'r', encoding='utf-8') as f:
            re_data = json.load(f)

        rel_count = 0
        for item in re_data:
            if item.get('relation') and item['relation'] != 'NONE':
                self.create_relation(
                    head=item['e1'],
                    relation=item['relation'],
                    tail=item['e2'],
                )
                rel_count += 1

        print(f"[KG] RE 抽取到 {rel_count} 条有效关系，导入完成！")

    # ------------------------------------------------------------------ #
    #  辅助
    # ------------------------------------------------------------------ #

    def clear_all(self):
        """清空所有知识图谱数据（谨慎使用！）"""
        with self.driver.session() as s:
            s.run("MATCH (n:KnowledgePoint) DETACH DELETE n")
        print("[KG] 已清空所有节点和关系")

    def get_stats(self) -> Dict:
        with self.driver.session() as s:
            node_cnt = s.run("MATCH (n:KnowledgePoint) RETURN count(n)").single()[0]
            rel_cnt = s.run("MATCH ()-[r]->() RETURN count(r)").single()[0]
        return {'nodes': node_cnt, 'relations': rel_cnt}

    def export_triples(self, output_path: str):
        """导出所有三元组为 JSON"""
        with self.driver.session() as s:
            result = s.run("""
                MATCH (a:KnowledgePoint)-[r]->(b:KnowledgePoint)
                RETURN a.name AS head, a.category AS head_type,
                       type(r) AS relation,
                       b.name AS tail, b.category AS tail_type,
                       a.course AS course
            """)
            triples = [dict(r) for r in result]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(triples, f, ensure_ascii=False, indent=2)
        print(f"[KG] 导出 {len(triples)} 条三元组到 {output_path}")


# ─────────────────────────────────────────────
#  示例数据：手动构建的核心三元组（用于快速测试）
# ─────────────────────────────────────────────
SAMPLE_TRIPLES = [
    # 线性结构
    {"head": "线性表", "head_type": "DS", "relation": "CONTAINS", "tail": "数组", "tail_type": "DS"},
    {"head": "线性表", "head_type": "DS", "relation": "CONTAINS", "tail": "链表", "tail_type": "DS"},
    {"head": "链表", "head_type": "DS", "relation": "CONTAINS", "tail": "单链表", "tail_type": "DS"},
    {"head": "链表", "head_type": "DS", "relation": "CONTAINS", "tail": "双向链表", "tail_type": "DS"},
    {"head": "链表", "head_type": "DS", "relation": "CONTAINS", "tail": "循环链表", "tail_type": "DS"},
    {"head": "数组", "head_type": "DS", "relation": "COMPARE", "tail": "链表", "tail_type": "DS"},
    {"head": "栈", "head_type": "DS", "relation": "BELONGS_TO", "tail": "线性表", "tail_type": "DS"},
    {"head": "队列", "head_type": "DS", "relation": "BELONGS_TO", "tail": "线性表", "tail_type": "DS"},
    {"head": "栈", "head_type": "DS", "relation": "RELATED", "tail": "队列", "tail_type": "DS"},
    {"head": "栈", "head_type": "DS", "relation": "IMPLEMENTS", "tail": "后进先出", "tail_type": "PRINCIPLE"},

    # 树
    {"head": "树", "head_type": "DS", "relation": "CONTAINS", "tail": "二叉树", "tail_type": "DS"},
    {"head": "二叉树", "head_type": "DS", "relation": "CONTAINS", "tail": "二叉搜索树", "tail_type": "DS"},
    {"head": "二叉搜索树", "head_type": "DS", "relation": "DERIVED_FROM", "tail": "二叉树", "tail_type": "DS"},
    {"head": "二叉搜索树", "head_type": "DS", "relation": "DERIVED_FROM", "tail": "AVL树", "tail_type": "DS"},
    {"head": "AVL树", "head_type": "DS", "relation": "DERIVED_FROM", "tail": "红黑树", "tail_type": "DS"},
    {"head": "二叉树", "head_type": "DS", "relation": "IMPLEMENTS", "tail": "递归", "tail_type": "METHOD"},
    {"head": "二叉树遍历", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "深度优先搜索", "tail_type": "ALGO"},
    {"head": "前序遍历", "head_type": "ALGO", "relation": "BELONGS_TO", "tail": "二叉树遍历", "tail_type": "ALGO"},
    {"head": "中序遍历", "head_type": "ALGO", "relation": "BELONGS_TO", "tail": "二叉树遍历", "tail_type": "ALGO"},
    {"head": "后序遍历", "head_type": "ALGO", "relation": "BELONGS_TO", "tail": "二叉树遍历", "tail_type": "ALGO"},
    {"head": "层序遍历", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "广度优先搜索", "tail_type": "ALGO"},
    {"head": "哈夫曼树", "head_type": "DS", "relation": "DERIVED_FROM", "tail": "二叉树", "tail_type": "DS"},

    # 堆
    {"head": "堆", "head_type": "DS", "relation": "DERIVED_FROM", "tail": "完全二叉树", "tail_type": "DS"},
    {"head": "最大堆", "head_type": "DS", "relation": "BELONGS_TO", "tail": "堆", "tail_type": "DS"},
    {"head": "最小堆", "head_type": "DS", "relation": "BELONGS_TO", "tail": "堆", "tail_type": "DS"},

    # 图
    {"head": "图", "head_type": "DS", "relation": "CONTAINS", "tail": "有向图", "tail_type": "DS"},
    {"head": "图", "head_type": "DS", "relation": "CONTAINS", "tail": "无向图", "tail_type": "DS"},
    {"head": "图", "head_type": "DS", "relation": "CONTAINS", "tail": "带权图", "tail_type": "DS"},
    {"head": "深度优先搜索", "head_type": "ALGO", "relation": "RELATED", "tail": "递归", "tail_type": "METHOD"},
    {"head": "广度优先搜索", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "队列", "tail_type": "DS"},
    {"head": "最短路径", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "Dijkstra算法", "tail_type": "ALGO"},
    {"head": "Dijkstra算法", "head_type": "ALGO", "relation": "BELONGS_TO", "tail": "最短路径", "tail_type": "ALGO"},
    {"head": "Floyd算法", "head_type": "ALGO", "relation": "BELONGS_TO", "tail": "最短路径", "tail_type": "ALGO"},
    {"head": "最小生成树", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "Prim算法", "tail_type": "ALGO"},
    {"head": "最小生成树", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "Kruskal算法", "tail_type": "ALGO"},

    # 排序
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "冒泡排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "选择排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "插入排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "归并排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "快速排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "堆排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "计数排序", "tail_type": "ALGO"},
    {"head": "排序算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "基数排序", "tail_type": "ALGO"},
    {"head": "快速排序", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "分治算法", "tail_type": "METHOD"},
    {"head": "归并排序", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "分治算法", "tail_type": "METHOD"},
    {"head": "堆排序", "head_type": "ALGO", "relation": "IMPLEMENTS", "tail": "堆", "tail_type": "DS"},

    # 查找
    {"head": "查找算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "顺序查找", "tail_type": "ALGO"},
    {"head": "查找算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "二分查找", "tail_type": "ALGO"},
    {"head": "查找算法", "head_type": "ALGO", "relation": "CONTAINS", "tail": "哈希查找", "tail_type": "ALGO"},
    {"head": "哈希表", "head_type": "DS", "relation": "IMPLEMENTS", "tail": "哈希查找", "tail_type": "ALGO"},
    {"head": "二分查找", "head_type": "ALGO", "relation": "PREREQUISITE", "tail": "有序数组", "tail_type": "DS"},

    # 算法思想
    {"head": "递归", "head_type": "METHOD", "relation": "RELATED", "tail": "分治算法", "tail_type": "METHOD"},
    {"head": "动态规划", "head_type": "METHOD", "relation": "DERIVED_FROM", "tail": "分治算法", "tail_type": "METHOD"},
    {"head": "贪心算法", "head_type": "METHOD", "relation": "RELATED", "tail": "动态规划", "tail_type": "METHOD"},
    {"head": "动态规划", "head_type": "METHOD", "relation": "CONTAINS", "tail": "最优子结构", "tail_type": "PRINCIPLE"},
    {"head": "动态规划", "head_type": "METHOD", "relation": "CONTAINS", "tail": "重叠子问题", "tail_type": "PRINCIPLE"},
]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='知识图谱构建工具')
    parser.add_argument('--uri', default='bolt://localhost:7687')
    parser.add_argument('--user', default='neo4j')
    parser.add_argument('--pwd', default='neo4j123')
    parser.add_argument('--triples', default='../data/kg_triples.json')
    parser.add_argument('--sample', action='store_true', help='使用内置示例数据')
    parser.add_argument('--export', type=str, help='导出三元组到指定文件')
    parser.add_argument('--stats', action='store_true', help='查看统计')
    parser.add_argument('--clear', action='store_true', help='清空图谱')
    args = parser.parse_args()

    builder = KnowledgeGraphBuilder(args.uri, args.user, args.pwd)

    if args.clear:
        builder.clear_all()
    elif args.stats:
        print(builder.get_stats())
    elif args.export:
        builder.export_triples(args.export)
    elif args.sample:
        # 先保存示例数据到文件
        sample_path = '../data/kg_triples_sample.json'
        with open(sample_path, 'w', encoding='utf-8') as f:
            json.dump(SAMPLE_TRIPLES, f, ensure_ascii=False, indent=2)
        builder.import_from_triples(sample_path, course='数据结构')
    elif os.path.exists(args.triples):
        builder.import_from_triples(args.triples, course='数据结构')
    else:
        print("请指定 --triples 文件路径或使用 --sample 加载示例数据")

    builder.close()
