"""
知识图谱 API
"""
from flask import Blueprint, request, jsonify
from app.services.kg_service import kg_service

kg_bp = Blueprint('kg', __name__)


@kg_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取知识图谱统计信息"""
    stats = kg_service.get_statistics()
    return jsonify({'code': 200, 'data': stats})


@kg_bp.route('/graph', methods=['GET'])
def get_full_graph():
    """获取完整知识图谱（前端可视化用）"""
    course = request.args.get('course')
    limit = int(request.args.get('limit', 500))
    graph = kg_service.get_full_graph(course=course, limit=limit)
    return jsonify({'code': 200, 'data': graph})


@kg_bp.route('/node/<path:name>', methods=['GET'])
def get_node(name: str):
    """获取单节点信息"""
    depth = int(request.args.get('depth', 2))
    result = kg_service.get_node_relations(name, depth=depth)
    return jsonify({'code': 200, 'data': result})


@kg_bp.route('/search', methods=['GET'])
def search_nodes():
    """搜索知识点"""
    keyword = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    if not keyword:
        return jsonify({'code': 400, 'message': '请输入搜索关键词'})
    nodes = kg_service.search_nodes(keyword, limit=limit)
    return jsonify({'code': 200, 'data': nodes})


@kg_bp.route('/node', methods=['POST'])
def create_node():
    """新增知识点节点"""
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'code': 400, 'message': '知识点名称不能为空'})
    kg_service.create_node(
        name=name,
        category=data.get('category', '概念'),
        course=data.get('course', '数据结构'),
        description=data.get('description', ''),
        difficulty=data.get('difficulty', 1),
    )
    return jsonify({'code': 200, 'message': '创建成功'})


@kg_bp.route('/relation', methods=['POST'])
def create_relation():
    """新增关系"""
    data = request.get_json()
    src = data.get('source', '').strip()
    tgt = data.get('target', '').strip()
    rel = data.get('relation', '').strip()
    if not all([src, tgt, rel]):
        return jsonify({'code': 400, 'message': '参数不完整'})
    kg_service.create_relation(src, rel, tgt)
    return jsonify({'code': 200, 'message': '关系创建成功'})


@kg_bp.route('/batch-import', methods=['POST'])
def batch_import():
    """批量导入三元组"""
    data = request.get_json()
    triples = data.get('triples', [])
    if not triples:
        return jsonify({'code': 400, 'message': '三元组列表为空'})
    count = kg_service.batch_import_triples(triples)
    return jsonify({'code': 200, 'data': {'imported': count}})
