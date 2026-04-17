"""
智能问答 API
"""
from flask import Blueprint, request, jsonify
from app.services.rag_service import rag_service

qa_bp = Blueprint('qa', __name__)


@qa_bp.route('/ask', methods=['POST'])
def ask():
    """
    智能问答接口
    Body: { "question": "什么是二叉树？", "user_id": 1 }
    """
    data = request.get_json()
    question = data.get('question', '').strip()
    user_id = data.get('user_id')

    if not question:
        return jsonify({'code': 400, 'message': '问题不能为空'})

    result = rag_service.answer(question, user_id=user_id)
    return jsonify({'code': 200, 'data': result})


@qa_bp.route('/history', methods=['GET'])
def get_history():
    """获取用户问答历史"""
    user_id = request.args.get('user_id', type=int)
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)

    if not user_id:
        return jsonify({'code': 400, 'message': '缺少 user_id'})

    from app.models.models import QAHistory
    query = QAHistory.query.filter_by(user_id=user_id).order_by(
        QAHistory.created_at.desc()
    )
    total = query.count()
    records = query.offset((page - 1) * size).limit(size).all()

    return jsonify({
        'code': 200,
        'data': {
            'total': total,
            'page': page,
            'list': [
                {
                    'id': r.id,
                    'question': r.question,
                    'answer': r.answer,
                    'retrieved_nodes': r.retrieved_nodes,
                    'rating': r.rating,
                    'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for r in records
            ]
        }
    })


@qa_bp.route('/rate', methods=['POST'])
def rate_answer():
    """对回答评分"""
    data = request.get_json()
    qa_id = data.get('id')
    rating = data.get('rating')

    if not qa_id or not rating:
        return jsonify({'code': 400, 'message': '参数不完整'})

    from app.models.models import QAHistory
    from app import db
    record = db.session.get(QAHistory, qa_id)
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在'})

    record.rating = int(rating)
    db.session.commit()
    return jsonify({'code': 200, 'message': '评分成功'})


@qa_bp.route('/build-index', methods=['POST'])
def build_index():
    """（管理员）重建 FAISS 向量索引"""
    data = request.get_json()
    chunks = data.get('chunks', [])
    if not chunks:
        # 从 Neo4j 自动获取知识点描述
        from app.services.kg_service import kg_service
        nodes = kg_service.get_all_nodes(limit=1000)
        chunks = [
            f"{n.get('name', '')}: {n.get('description', '')}"
            for n in nodes if n.get('description')
        ]

    if not chunks:
        return jsonify({'code': 400, 'message': '没有可用的文本块'})

    rag_service.build_index(chunks)
    return jsonify({'code': 200, 'data': {'chunk_count': len(chunks)}})
