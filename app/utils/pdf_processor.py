import pdfplumber
import os
import uuid
from werkzeug.utils import secure_filename

def extract_text_from_pdf(pdf_path):
    """Extrai o texto de um arquivo PDF"""
    text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
                    
            return text, len(pdf.pages)
    except Exception as e:
        print(f"Erro ao processar PDF: {e}")
        return None, 0

def save_pdf_file(pdf_file, upload_folder):
    """Salva o arquivo PDF no servidor e retorna o caminho relativo"""
    filename = secure_filename(pdf_file.filename)
    # Adiciona um identificador único para evitar conflitos de nome
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    
    file_path = os.path.join(upload_folder, unique_filename)
    pdf_file.save(file_path)
    
    # Retorna o caminho relativo para armazenar no banco de dados
    return unique_filename, file_path, pdf_file.content_length 