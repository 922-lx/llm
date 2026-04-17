"""
Flask 应用工厂
"""
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name='default'):
    app = Flask(__name__)

    # 加载配置
    from config import config
    app.config.from_object(config[config_name])

    # 初始化扩展
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # 注册蓝图
    from app.api.kg_api import kg_bp
    from app.api.qa_api import qa_bp
    from app.api.recommend_api import recommend_bp
    from app.api.user_api import user_bp

    app.register_blueprint(kg_bp, url_prefix='/api/kg')
    app.register_blueprint(qa_bp, url_prefix='/api/qa')
    app.register_blueprint(recommend_bp, url_prefix='/api/recommend')
    app.register_blueprint(user_bp, url_prefix='/api/user')

    # 健康检查
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': '数据结构智能问答系统运行中'}

    return app
