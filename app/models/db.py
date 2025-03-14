from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def init_app(app):
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # Cria as tabelas se não existirem
    with app.app_context():
        # Importa todos os modelos para garantir que o SQLAlchemy os conheça
        from app.models.user import User
        from app.models.pdf import PDF, AudioFile
        
        # Cria todas as tabelas
        db.create_all() 