from app.models.db import db
from datetime import datetime

class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # Tamanho em bytes
    page_count = db.Column(db.Integer)
    
    # Caminho relativo para o arquivo PDF
    file_path = db.Column(db.String(300))
    
    # Relacionamento com o usuário
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relacionamento com os áudios
    audio_files = db.relationship('AudioFile', backref='pdf', lazy=True, cascade="all, delete-orphan")
    
    def get_status(self):
        if not self.audio_files:
            return "Pendente"
        else:
            return "Convertido"


class AudioFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    file_path = db.Column(db.String(300))
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Float, nullable=True)  # Duração em segundos
    
    # Relacionamento com o PDF
    pdf_id = db.Column(db.Integer, db.ForeignKey('PDF.id'), nullable=False) 