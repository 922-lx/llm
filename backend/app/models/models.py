"""
MySQL 数据模型（SQLAlchemy ORM）
"""
from datetime import datetime
from sqlalchemy import Text
from app import db


class User(db.Model):
    """学生/用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, comment='用户名')
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(16), default='student', comment='角色: student/teacher/admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    learning_records = db.relationship('LearningRecord', backref='user', lazy='dynamic')
    qa_history = db.relationship('QAHistory', backref='user', lazy='dynamic')


class KnowledgePoint(db.Model):
    """知识点表（原始数据）"""
    __tablename__ = 'knowledge_points'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, comment='知识点名称')
    course = db.Column(db.String(64), comment='所属课程')
    category = db.Column(db.String(64), comment='类别: 概念/原理/算法/数据结构')
    description = db.Column(db.Text, comment='描述')
    difficulty = db.Column(db.Integer, default=1, comment='难度 1-5')
    neo4j_node_id = db.Column(db.String(64), comment='Neo4j节点ID')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Exercise(db.Model):
    """习题表"""
    __tablename__ = 'exercises'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False, comment='题目')
    type = db.Column(db.String(32), comment='题型: 选择/填空/编程/简答')
    answer = db.Column(db.Text, comment='参考答案')
    analysis = db.Column(db.Text, comment='解析')
    difficulty = db.Column(db.Integer, default=1, comment='难度 1-5')
    course = db.Column(db.String(64))
    knowledge_point_ids = db.Column(db.JSON, comment='关联知识点ID列表')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LearningRecord(db.Model):
    """学习记录表"""
    __tablename__ = 'learning_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    knowledge_point_id = db.Column(db.Integer, db.ForeignKey('knowledge_points.id'))
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'))
    score = db.Column(db.Float, comment='得分 0-1')
    is_correct = db.Column(db.Boolean)
    time_spent = db.Column(db.Integer, comment='用时（秒）')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class QAHistory(db.Model):
    """问答历史表"""
    __tablename__ = 'qa_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    retrieved_nodes = db.Column(db.JSON, comment='RAG检索到的知识点')
    rating = db.Column(db.Integer, comment='用户评分 1-5')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RawData(db.Model):
    """原始数据暂存表"""
    __tablename__ = 'raw_data'

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(256), comment='来源URL/文件名')
    source_type = db.Column(db.String(32), comment='类型: textbook/paper/course')
    content = db.Column(db.Text, comment='原始文本')
    processed = db.Column(db.Boolean, default=False, comment='是否已处理')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
