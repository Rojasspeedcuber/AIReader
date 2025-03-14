from app.models.db import db
from datetime import datetime

class PDF(db.Model):
    __tablename__ = 'pdf'  # Definindo explicitamente o nome da tabela em minúsculas
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # Tamanho em bytes
    page_count = db.Column(db.Integer)
    
    # Caminho relativo para o arquivo PDF
    file_path = db.Column(db.String(300))
    
    # Status de processamento
    is_processing = db.Column(db.Boolean, default=False)
    
    # Relacionamento com o usuário
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relacionamento com os áudios
    audio_files = db.relationship('AudioFile', backref='pdf', lazy=True, cascade="all, delete-orphan")
    
    def get_status(self):
        # Verifica se o atributo is_processing existe e é True
        try:
            if hasattr(self, 'is_processing') and self.is_processing:
                return "Em Processamento"
        except:
            # Ignora erros se a coluna ainda não existe
            pass
        
        # Verifica se existem arquivos de áudio
        if not self.audio_files:
            return "Pendente"
        else:
            return "Convertido"


class AudioFile(db.Model):
    __tablename__ = 'audio_file'  # Definindo explicitamente o nome da tabela
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    file_path = db.Column(db.String(300))
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Float, nullable=True)  # Duração em segundos
    
    # Relacionamento com o PDF - corrigindo a referência para usar o nome da tabela em minúsculas
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf.id'), nullable=False)