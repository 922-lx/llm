"""
知识图谱服务层 —— 封装 Neo4j 操作
"""
from neo4j import GraphDatabase
from flask import current_app
from typing import List, Dict, Optional


class KGService:
    """
    知识图谱服务：实体查询、关系查询、子图获取、三元组写入等
    """

    def __init__(self):
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            uri = current_app.config['NEO4J_URI']
            user = current_app.config['NEO4J_USER']
            pwd = current_app.config['NEO4J_PASSWORD']
            self._driver = GraphDatabase.driver(uri, auth=(user, pwd))
        return self._driver

    # ------------------------------------------------------------------ #
    #  基础查询
    # ------------------------------------------------------------------ #

    def get_node_by_name(self, name: str) -> Optional[Dict]:
        """按名称查询知识点节点"""
        with self._get_driver().session() as session:
            result = session.run(
                "MATCH (n:KnowledgePoint {name: $name}) RETURN n",
                name=name
            )
            record = result.single()
            if record:
                node = record['n']
                return dict(node)
        return None

    def search_nodes(self, keyword: str, limit: int = 20) -> List[Dict]:
        """模糊搜索知识点"""
        with self._get_driver().session() as session:
            result = session.run(
                """
                MATCH (n:KnowledgePoint)
                WHERE n.name CONTAINS $kw OR n.description CONTAINS $kw
                RETURN n LIMIT $limit
                """,
                kw=keyword, limit=limit
            )
            return [dict(r['n']) for r in result]

    def get_node_relations(self, name: str, depth: int = 2) -> Dict:
        """
        获取以指定节点为中心的子图（nodes + links），用于前端可视化。
        depth: 扩展层数（最大3）
        """
        depth = min(depth, 3)
        with self._get_driver().session() as session:
            result = session.run(
                f"""
                MATCH path = (start:KnowledgePoint {{name: $name}})-[*1..{depth}]-(end:KnowledgePoint)
                WITH nodes(path) AS ns, relationships(path) AS rs
                UNWIND ns AS n
                WITH collect(DISTINCT n) AS allNodes, rs
                UNWIND rs AS r
                WITH allNodes, collect(DISTINCT r) AS allRels
                RETURN allNodes, allRels
                """,
                name=name
            )
            record = result.single()
            if not record:
                # 只有孤立节点
                node = self.get_node_by_name(name)
                if node:
                    return {'nodes': [{'id': node.get('name'), 'label': node.get('name'),
                                       'category': node.get('category', '概念')}],
                            'links': []}
                return {'nodes': [], 'links': []}

            all_nodes = record['allNodes']
            all_rels = record['allRels']

            nodes = []
            node_ids = set()
            for n in all_nodes:
                nd = dict(n)
                nid = nd.get('name', str(n.id))
                if nid not in node_ids:
                    node_ids.add(nid)
                    nodes.append({
                        'id': nid,
                        'label': nd.get('name', nid),
                        'category': nd.get('category', '概念'),
                        'difficulty': nd.get('difficulty', 1),
                        'description': nd.get('description', ''),
                    })

            links = []
            for r in all_rels:
                src = dict(r.start_node).get('name', '')
                tgt = dict(r.end_node).get('name', '')
                links.append({
                    'source': src,
                    'target': tgt,
                    'relation': r.type,
                })

            return {'nodes': nodes, 'links': links}

    def get_all_nodes(self, course: str = None, limit: int = 200) -> List[Dict]:
        """获取所有知识点（可按课程过滤）"""
        with self._get_driver().session() as session:
            if course:
                result = session.run(
                    "MATCH (n:KnowledgePoint {course: $course}) RETURN n LIMIT $limit",
                    course=course, limit=limit
                )
            else:
                result = session.run(
                    "MATCH (n:KnowledgePoint) RETURN n LIMIT $limit",
                    limit=limit
                )
            return [dict(r['n']) for r in result]

    def get_full_graph(self, course: str = None, limit: int = 500) -> Dict:
        """获取完整知识图谱（nodes + links）"""
        with self._get_driver().session() as session:
            if course:
                result = session.run(
                    """
                    MATCH (a:KnowledgePoint {course: $course})-[r]->(b:KnowledgePoint {course: $course})
                    RETURN a, r, b LIMIT $limit
                    """,
                    course=course, limit=limit
                )
            else:
                result = session.run(
                    "MATCH (a:KnowledgePoint)-[r]->(b:KnowledgePoint) RETURN a, r, b LIMIT $limit",
                    limit=limit
                )

            nodes_map = {}
            links = []
            for record in result:
                for key in ('a', 'b'):
                    nd = dict(record[key])
                    nid = nd.get('name', '')
                    if nid and nid not in nodes_map:
                        nodes_map[nid] = {
                            'id': nid,
                            'label': nid,
                            'category': nd.get('category', '概念'),
                            'difficulty': nd.get('difficulty', 1),
                        }
                src = dict(record['a']).get('name', '')
                tgt = dict(record['b']).get('name', '')
                rel = record['r'].type
                links.append({'source': src, 'target': tgt, 'relation': rel})

            return {'nodes': list(nodes_map.values()), 'links': links}

    # ------------------------------------------------------------------ #
    #  写入
    # ------------------------------------------------------------------ #

    def create_node(self, name: str, category: str, course: str,
                    description: str = '', difficulty: int = 1) -> bool:
        """创建或更新知识点节点"""
        with self._get_driver().session() as session:
            session.run(
                """
                MERGE (n:KnowledgePoint {name: $name})
                SET n.category = $category, n.course = $course,
                    n.description = $description, n.difficulty = $difficulty
                """,
                name=name, category=category, course=course,
                description=description, difficulty=difficulty
            )
        return True

    def create_relation(self, src: str, rel_type: str, tgt: str) -> bool:
        """创建关系（两节点必须已存在）"""
        with self._get_driver().session() as session:
            session.run(
                f"""
                MATCH (a:KnowledgePoint {{name: $src}})
                MATCH (b:KnowledgePoint {{name: $tgt}})
                MERGE (a)-[:{rel_type}]->(b)
                """,
                src=src, tgt=tgt
            )
        return True

    def batch_import_triples(self, triples: List[Dict]) -> int:
        """
        批量导入三元组
        triple: {'head': str, 'head_type': str, 'relation': str,
                 'tail': str, 'tail_type': str, 'course': str}
        """
        count = 0
        with self._get_driver().session() as session:
            for t in triples:
                try:
                    session.run(
                        """
                        MERGE (a:KnowledgePoint {name: $head})
                        SET a.category = $head_type, a.course = $course
                        MERGE (b:KnowledgePoint {name: $tail})
                        SET b.category = $tail_type, b.course = $course
                        MERGE (a)-[:""" + t['relation'] + """]->(b)
                        """,
                        head=t['head'], head_type=t.get('head_type', '概念'),
                        tail=t['tail'], tail_type=t.get('tail_type', '概念'),
                        course=t.get('course', '数据结构')
                    )
                    count += 1
                except Exception:
                    continue
        return count

    def get_statistics(self) -> Dict:
        """获取知识图谱统计信息"""
        with self._get_driver().session() as session:
            node_count = session.run("MATCH (n:KnowledgePoint) RETURN count(n) AS cnt").single()['cnt']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()['cnt']
            courses = session.run(
                "MATCH (n:KnowledgePoint) RETURN DISTINCT n.course AS course, count(n) AS cnt"
            )
            course_stats = {r['course']: r['cnt'] for r in courses if r['course']}
        return {
            'node_count': node_count,
            'relation_count': rel_count,
            'course_stats': course_stats,
        }


kg_service = KGService()
