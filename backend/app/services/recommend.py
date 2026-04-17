"""
个性化学习路径与习题推荐服务
- 基于学生知识点掌握度（历史记录）
- 协同过滤 + 知识图谱路径规划
"""
from typing import List, Dict, Tuple
from collections import defaultdict
import random


class RecommendService:

    # ------------------------------------------------------------------ #
    #  习题推荐
    # ------------------------------------------------------------------ #

    def recommend_exercises(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        个性化习题推荐：
        1. 计算各知识点掌握度
        2. 找掌握度最低的知识点
        3. 推荐该知识点相关习题（排除已做对的）
        """
        from app.models.models import LearningRecord, Exercise, KnowledgePoint
        from app import db

        # 1. 获取该用户所有学习记录
        records = db.session.query(LearningRecord).filter_by(user_id=user_id).all()
        if not records:
            # 新用户：推荐基础难度题目
            exercises = db.session.query(Exercise).filter(
                Exercise.difficulty <= 2
            ).order_by(Exercise.difficulty).limit(limit).all()
            return [self._exercise_to_dict(e) for e in exercises]

        # 2. 统计每个知识点的掌握度
        kp_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        for rec in records:
            if rec.knowledge_point_id:
                kp_stats[rec.knowledge_point_id]['total'] += 1
                if rec.is_correct:
                    kp_stats[rec.knowledge_point_id]['correct'] += 1

        mastery = {
            kp_id: s['correct'] / s['total'] if s['total'] > 0 else 0.0
            for kp_id, s in kp_stats.items()
        }

        # 3. 找掌握度最低的 N 个知识点
        weak_kp_ids = sorted(mastery.keys(), key=lambda x: mastery[x])[:5]

        # 4. 查找相关习题
        correct_exercise_ids = {
            rec.exercise_id for rec in records
            if rec.is_correct and rec.exercise_id
        }

        exercises = []
        for kp_id in weak_kp_ids:
            results = db.session.query(Exercise).filter(
                Exercise.knowledge_point_ids.contains(str(kp_id)),
                ~Exercise.id.in_(correct_exercise_ids)
            ).order_by(Exercise.difficulty).limit(3).all()
            exercises.extend(results)

        # 去重 + 限制数量
        seen = set()
        final = []
        for e in exercises:
            if e.id not in seen:
                seen.add(e.id)
                final.append(self._exercise_to_dict(e))
            if len(final) >= limit:
                break

        # 随机打乱顺序，让"换一批"感觉不同
        random.shuffle(final)

        # 补充通用题目
        if len(final) < limit:
            extra = db.session.query(Exercise).filter(
                ~Exercise.id.in_([e['id'] for e in final])
            ).order_by(db.func.random()).limit(limit - len(final)).all()
            final.extend([self._exercise_to_dict(e) for e in extra])

        return final

    # ------------------------------------------------------------------ #
    #  学习路径推荐
    # ------------------------------------------------------------------ #

    def recommend_learning_path(self, user_id: int, target_kp: str = None) -> Dict:
        """
        推荐学习路径：
        1. 若指定目标知识点，规划从薄弱点到目标的最短路径
        2. 若未指定，推荐从当前薄弱点出发的渐进路径
        """
        from app.services.kg_service import kg_service
        from app.models.models import LearningRecord, KnowledgePoint
        from app import db

        # 获取薄弱知识点
        records = db.session.query(LearningRecord).filter_by(user_id=user_id).all()
        weak_kps = self._get_weak_kps(records)

        if target_kp:
            path = self._find_path(weak_kps[0] if weak_kps else '数组', target_kp, kg_service)
        else:
            # 默认推荐：从基础数据结构到高级算法
            default_path = self._get_default_path()
            # 过滤已掌握的
            mastered = self._get_mastered_kps(records)
            path = [p for p in default_path if p not in mastered]

        return {
            'path': path,
            'weak_points': weak_kps[:5],
            'total_steps': len(path),
        }

    def _get_weak_kps(self, records) -> List[str]:
        """获取薄弱知识点名称列表"""
        from app.models.models import KnowledgePoint
        from app import db
        kp_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        for rec in records:
            if rec.knowledge_point_id:
                kp_stats[rec.knowledge_point_id]['total'] += 1
                if rec.is_correct:
                    kp_stats[rec.knowledge_point_id]['correct'] += 1

        weak_ids = sorted(
            kp_stats.keys(),
            key=lambda x: kp_stats[x]['correct'] / kp_stats[x]['total'] if kp_stats[x]['total'] > 0 else 0
        )[:10]

        names = []
        for kid in weak_ids:
            kp = db.session.get(KnowledgePoint, kid)
            if kp:
                names.append(kp.name)
        return names

    def _get_mastered_kps(self, records, threshold: float = 0.8) -> List[str]:
        """获取已掌握知识点（正确率 >= threshold）"""
        from app.models.models import KnowledgePoint
        from app import db
        kp_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        for rec in records:
            if rec.knowledge_point_id:
                kp_stats[rec.knowledge_point_id]['total'] += 1
                if rec.is_correct:
                    kp_stats[rec.knowledge_point_id]['correct'] += 1

        mastered = []
        for kid, s in kp_stats.items():
            if s['total'] > 0 and s['correct'] / s['total'] >= threshold:
                kp = db.session.get(KnowledgePoint, kid)
                if kp:
                    mastered.append(kp.name)
        return mastered

    @staticmethod
    def _find_path(start: str, end: str, kg_service) -> List[str]:
        """利用 BFS 在知识图谱中寻找两节点间最短路径"""
        try:
            with kg_service._get_driver().session() as session:
                result = session.run(
                    """
                    MATCH path = shortestPath(
                        (a:KnowledgePoint {name: $start})-[*]-(b:KnowledgePoint {name: $end})
                    )
                    RETURN [n IN nodes(path) | n.name] AS path_names
                    """,
                    start=start, end=end
                )
                record = result.single()
                if record:
                    return record['path_names']
        except Exception:
            pass
        return [start, end]

    @staticmethod
    def _get_default_path() -> List[str]:
        """默认《数据结构》学习路径"""
        return [
            '数组', '链表', '栈', '队列',
            '递归', '树', '二叉树', '二叉搜索树', 'AVL树', '红黑树',
            '堆', '图', 'BFS', 'DFS',
            '排序算法', '冒泡排序', '选择排序', '插入排序',
            '归并排序', '快速排序', '堆排序',
            '查找算法', '顺序查找', '二分查找', '哈希查找',
            '动态规划', '贪心算法', '分治算法',
        ]

    @staticmethod
    def _exercise_to_dict(e) -> Dict:
        title = e.title or ''
        # 从题目文本中提取选项（支持 A. B. C. D. 格式）
        options = []
        import re
        opts = re.findall(r'([A-D])\.\s*(.+?)(?=\s+[A-D]\.|$)', title)
        if opts:
            options = [{'label': o[0], 'text': o[1].strip()} for o in opts]
            # 清理 title 中的选项部分，只保留题干
            clean_title = re.split(r'\s+[A-D]\.', title)[0].strip()
        else:
            clean_title = title

        return {
            'id': e.id,
            'title': clean_title,
            'type': e.type,
            'difficulty': e.difficulty,
            'course': e.course,
            'answer': e.answer,
            'analysis': e.analysis,
            'options': options,
        }


recommend_service = RecommendService()
