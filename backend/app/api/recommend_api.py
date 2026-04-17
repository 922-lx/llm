"""
推荐系统 API
"""
from flask import Blueprint, request, jsonify
from app.services.recommend import recommend_service

recommend_bp = Blueprint('recommend', __name__)


@recommend_bp.route('/exercises', methods=['GET'])
def recommend_exercises():
    """个性化习题推荐"""
    user_id = request.args.get('user_id', type=int)
    limit = request.args.get('limit', 10, type=int)
    if not user_id:
        return jsonify({'code': 400, 'message': '缺少 user_id'})
    exercises = recommend_service.recommend_exercises(user_id, limit=limit)
    return jsonify({'code': 200, 'data': exercises})


@recommend_bp.route('/learning-path', methods=['GET'])
def recommend_path():
    """学习路径推荐"""
    user_id = request.args.get('user_id', type=int)
    target = request.args.get('target')
    if not user_id:
        return jsonify({'code': 400, 'message': '缺少 user_id'})
    path = recommend_service.recommend_learning_path(user_id, target_kp=target)
    return jsonify({'code': 200, 'data': path})


@recommend_bp.route('/submit-answer', methods=['POST'])
def submit_answer():
    """提交答题记录"""
    data = request.get_json()
    user_id = data.get('user_id')
    exercise_id = data.get('exercise_id')
    is_correct = data.get('is_correct', False)
    time_spent = data.get('time_spent', 0)

    if not user_id or not exercise_id:
        return jsonify({'code': 400, 'message': '参数不完整'})

    from app.models.models import LearningRecord, Exercise
    from app import db

    exercise = db.session.get(Exercise, exercise_id)
    kp_ids = exercise.knowledge_point_ids if exercise else []

    for kp_id in (kp_ids or []):
        record = LearningRecord(
            user_id=user_id,
            knowledge_point_id=kp_id,
            exercise_id=exercise_id,
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            time_spent=time_spent,
        )
        db.session.add(record)

    if not kp_ids:
        record = LearningRecord(
            user_id=user_id,
            exercise_id=exercise_id,
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            time_spent=time_spent,
        )
        db.session.add(record)

    db.session.commit()
    return jsonify({'code': 200, 'message': '提交成功'})


@recommend_bp.route('/mastery', methods=['GET'])
def get_mastery():
    """获取用户知识点掌握情况"""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'code': 400, 'message': '缺少 user_id'})

    from app.models.models import LearningRecord, KnowledgePoint
    from app import db
    from collections import defaultdict

    records = db.session.query(LearningRecord).filter_by(user_id=user_id).all()
    kp_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    for rec in records:
        if rec.knowledge_point_id:
            kp_stats[rec.knowledge_point_id]['total'] += 1
            if rec.is_correct:
                kp_stats[rec.knowledge_point_id]['correct'] += 1

    result = []
    for kp_id, stats in kp_stats.items():
        kp = db.session.get(KnowledgePoint, kp_id)
        if kp:
            mastery = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            result.append({
                'kp_id': kp_id,
                'name': kp.name,
                'category': kp.category,
                'mastery': round(mastery, 3),
                'total': stats['total'],
                'correct': stats['correct'],
            })

    result.sort(key=lambda x: x['mastery'])
    return jsonify({'code': 200, 'data': result})
