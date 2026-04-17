"""
用户 API（登录、注册、个人信息）
"""
import hashlib
from flask import Blueprint, request, jsonify, session

user_bp = Blueprint('user', __name__)


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'student')

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

    from app.models.models import User
    from app import db

    if User.query.filter_by(username=username).first():
        return jsonify({'code': 409, 'message': '用户名已存在'})

    user = User(username=username, password_hash=hash_password(password), role=role)
    db.session.add(user)
    db.session.commit()
    return jsonify({'code': 200, 'message': '注册成功', 'data': {'id': user.id}})


@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    from app.models.models import User

    user = User.query.filter_by(
        username=username, password_hash=hash_password(password)
    ).first()

    if not user:
        return jsonify({'code': 401, 'message': '用户名或密码错误'})

    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
        }
    })


@user_bp.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id: int):
    from app.models.models import User, LearningRecord, QAHistory
    from app import db

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'})

    total_qa = QAHistory.query.filter_by(user_id=user_id).count()
    total_exercises = LearningRecord.query.filter_by(user_id=user_id).count()
    correct_exercises = LearningRecord.query.filter_by(
        user_id=user_id, is_correct=True
    ).count()

    return jsonify({
        'code': 200,
        'data': {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'total_qa': total_qa,
            'total_exercises': total_exercises,
            'correct_rate': round(correct_exercises / total_exercises, 3) if total_exercises else 0,
            'created_at': user.created_at.strftime('%Y-%m-%d'),
        }
    })
