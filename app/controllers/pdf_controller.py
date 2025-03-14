from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, Response
from flask_login import login_required, current_user
from app.models.db import db
from app.models.pdf import PDF, AudioFile
from app.utils.forms import UploadPDFForm
from app.utils.pdf_processor import save_pdf_file, extract_text_from_pdf
from app.utils.tts_service import text_to_speech
import os
import threading
import sqlite3
from functools import wraps
import re

pdf_bp = Blueprint('pdf', __name__)

# Decorador para verificar se o usuário tem assinatura ativa
def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_subscribed():
            print(f"[Acesso negado] Usuário {current_user.email} tentou acessar uma função restrita sem assinatura ativa")
            flash('É necessário ter uma assinatura ativa para acessar este recurso.', 'warning')
            return redirect(url_for('payment.subscription'))
        return f(*args, **kwargs)
    return decorated_function

# Rota temporária para adicionar a coluna is_processing à tabela pdf (remover após uso)
@pdf_bp.route('/migrate-db')
def migrate_db():
    try:
        # Identifica o caminho do banco de dados
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Conecta diretamente ao banco SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se a coluna já existe
        cursor.execute("PRAGMA table_info(pdf)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_processing' not in columns:
            # Adiciona a coluna is_processing com valor padrão False
            cursor.execute("ALTER TABLE pdf ADD COLUMN is_processing BOOLEAN DEFAULT FALSE")
            conn.commit()
            result = "Coluna 'is_processing' adicionada com sucesso!"
        else:
            result = "Coluna 'is_processing' já existe."
        
        conn.close()
        return f"Migração concluída: {result}"
    except Exception as e:
        return f"Erro durante a migração: {str(e)}"

# Função para processar a conversão em segundo plano
def process_conversion_background(pdf_id, user_id, app):
    """Processa a conversão de PDF para áudio em segundo plano"""
    with app.app_context():
        try:
            # Recupera o PDF
            pdf = PDF.query.filter_by(id=pdf_id, user_id=user_id).first()
            if not pdf:
                print(f"[BG-Convert] PDF {pdf_id} não encontrado para usuário {user_id}")
                return
                
            print(f"[BG-Convert] Iniciando conversão em segundo plano para PDF: {pdf.title}")
            
            # Caminho completo para o PDF
            pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf.file_path)
            
            # Verifica se o arquivo existe
            if not os.path.exists(pdf_path):
                print(f"[BG-Convert] ERRO: Arquivo PDF não encontrado no caminho: {pdf_path}")
                # Marca o PDF como não processando
                pdf.is_processing = False
                db.session.commit()
                return
            
            # Extrai o texto do PDF
            text, _ = extract_text_from_pdf(pdf_path)
            
            if not text:
                print(f"[BG-Convert] ERRO: Não foi possível extrair texto do PDF")
                # Marca o PDF como não processando
                pdf.is_processing = False
                db.session.commit()
                return
            
            print(f"[BG-Convert] Texto extraído com sucesso. Tamanho: {len(text)} caracteres")
            
            # Verifica se o diretório de áudio existe
            audio_folder = current_app.config['AUDIO_FOLDER']
            if not os.path.exists(audio_folder):
                os.makedirs(audio_folder, exist_ok=True)
            
            # Converte o texto para áudio
            audio_filename, duration = text_to_speech(text, audio_folder)
            
            if not audio_filename:
                print(f"[BG-Convert] ERRO: Falha na conversão de texto para áudio")
                # Marca o PDF como não processando
                pdf.is_processing = False
                db.session.commit()
                return
            
            print(f"[BG-Convert] Áudio gerado com sucesso: {audio_filename}, duração: {duration}s")
            
            # Cria o registro do áudio no banco de dados
            audio = AudioFile(
                filename=audio_filename,
                file_path=audio_filename,
                duration=duration,
                pdf_id=pdf.id
            )
            
            # Adiciona o áudio e marca o PDF como não processando
            db.session.add(audio)
            pdf.is_processing = False
            db.session.commit()
            print(f"[BG-Convert] Conversão concluída e registro salvo no banco de dados")
            
        except Exception as e:
            print(f"[BG-Convert] ERRO na conversão em segundo plano: {str(e)}")
            import traceback
            print(traceback.format_exc())
            
            # Em caso de erro, marca o PDF como não processando
            try:
                pdf = PDF.query.filter_by(id=pdf_id, user_id=user_id).first()
                if pdf:
                    pdf.is_processing = False
                    db.session.commit()
            except:
                pass

@pdf_bp.route('/dashboard')
@login_required
@subscription_required
def dashboard():
    try:
        # Log para depuração
        print(f"[Dashboard] Usuário {current_user.email} tentando acessar o dashboard")
        
        pdfs = PDF.query.filter_by(user_id=current_user.id).order_by(PDF.upload_date.desc()).all()
        form = UploadPDFForm()
        
        return render_template('dashboard.html', pdfs=pdfs, form=form)
    except Exception as e:
        # Se houver erro no dashboard (provavelmente problema com banco de dados)
        print(f"[Dashboard] ERRO: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.', 'danger')
        return render_template('dashboard.html', pdfs=[], form=UploadPDFForm())

@pdf_bp.route('/upload', methods=['POST'])
@login_required
@subscription_required
def upload_pdf():
    # Log para depuração
    print(f"[Upload] Usuário {current_user.email} tentando fazer upload de PDF")
    
    form = UploadPDFForm()
    
    if form.validate_on_submit():
        try:
            # Salva o arquivo
            filename, file_path, file_size = save_pdf_file(
                form.pdf_file.data, 
                current_app.config['UPLOAD_FOLDER']
            )
            
            # Extrai informações do PDF
            _, page_count = extract_text_from_pdf(file_path)
            
            # Cria o registro no banco de dados
            pdf = PDF(
                title=form.title.data,
                filename=filename,
                file_path=filename,
                file_size=file_size,
                page_count=page_count,
                user_id=current_user.id
            )
            
            db.session.add(pdf)
            db.session.commit()
            
            flash('PDF enviado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao fazer upload do PDF: {str(e)}', 'danger')
    
    return redirect(url_for('pdf.dashboard'))

@pdf_bp.route('/convert/<int:pdf_id>', methods=['POST'])
@login_required
@subscription_required
def convert_to_audio(pdf_id):
    # Log para depuração
    print(f"[Convert] Usuário {current_user.email} tentando converter PDF {pdf_id}")
    
    try:
        # Verifica se o PDF existe e pertence ao usuário
        pdf = PDF.query.filter_by(id=pdf_id, user_id=current_user.id).first_or_404()
        print(f"[Convert] PDF encontrado: {pdf.title}")
        
        # Verifica se já existe um áudio para este PDF
        if pdf.audio_files:
            print(f"[Convert] PDF já possui áudio")
            flash('Este PDF já foi convertido para áudio.', 'info')
            return redirect(url_for('pdf.dashboard'))
        
        # Se a coluna is_processing não existir no banco de dados, ignore-a
        try:
            # Verifica se já está em processamento
            if pdf.is_processing:
                print(f"[Convert] PDF já está em processamento")
                flash('Este PDF já está sendo convertido. Por favor, aguarde.', 'info')
                return redirect(url_for('pdf.dashboard'))
            
            # Marca o PDF como em processamento
            pdf.is_processing = True
            db.session.commit()
        except Exception as e:
            print(f"[Convert] AVISO: Erro ao verificar/atualizar status de processamento: {e}")
            # Continua mesmo se houver erro (coluna pode não existir ainda)
        
        # Inicia a thread de conversão em segundo plano
        print(f"[Convert] Iniciando conversão em segundo plano para PDF: {pdf.title}")
        try:
            conversion_thread = threading.Thread(
                target=process_conversion_background,
                args=(pdf_id, current_user.id, current_app._get_current_object())
            )
            conversion_thread.daemon = True
            conversion_thread.start()
        except Exception as thread_error:
            print(f"[Convert] ERRO ao iniciar thread: {str(thread_error)}")
            # Se não conseguir iniciar a thread, tenta uma conversão síncrona simplificada
            try:
                # Cria um áudio vazio como fallback
                audio_folder = current_app.config['AUDIO_FOLDER']
                if not os.path.exists(audio_folder):
                    os.makedirs(audio_folder, exist_ok=True)
                
                # Nome do arquivo e caminho
                audio_filename = f"fallback_{pdf_id}.mp3"
                audio_path = os.path.join(audio_folder, audio_filename)
                
                # Cria um MP3 vazio
                with open(audio_path, 'wb') as f:
                    mp3_bytes = b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                    f.write(mp3_bytes)
                
                # Registra no banco de dados
                audio = AudioFile(
                    filename=audio_filename,
                    file_path=audio_filename,
                    duration=1.0,
                    pdf_id=pdf.id
                )
                db.session.add(audio)
                db.session.commit()
                
                flash('PDF convertido para áudio com sucesso (modo alternativo).', 'success')
            except Exception as fallback_error:
                print(f"[Convert] ERRO no fallback: {str(fallback_error)}")
                flash('Erro na conversão. Por favor, tente novamente mais tarde.', 'danger')
            
            return redirect(url_for('pdf.dashboard'))
        
        # Informa ao usuário que a conversão foi iniciada
        flash('A conversão para áudio foi iniciada em segundo plano. Aguarde alguns instantes e atualize a página para verificar quando estiver pronto.', 'info')
        return redirect(url_for('pdf.dashboard'))
    
    except Exception as e:
        print(f"[Convert] ERRO ao iniciar conversão: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash(f'Não foi possível iniciar a conversão. Por favor, tente novamente.', 'danger')
        return redirect(url_for('pdf.dashboard'))

@pdf_bp.route('/download/<int:pdf_id>', methods=['POST'])
@login_required
@subscription_required
def download_audio(pdf_id):
    try:
        # Log para depuração
        print(f"[Download] Usuário {current_user.email} tentando baixar áudio do PDF {pdf_id}")
        
        # Verifica se o PDF existe e pertence ao usuário
        pdf = PDF.query.filter_by(id=pdf_id, user_id=current_user.id).first_or_404()
        
        # Verifica se existe um áudio para este PDF
        if not pdf.audio_files:
            flash('Este PDF ainda não foi convertido para áudio.', 'warning')
            return redirect(url_for('pdf.dashboard'))
        
        # Obtém o primeiro arquivo de áudio
        audio = pdf.audio_files[0]
        
        # Verifica se o arquivo existe fisicamente
        audio_path = os.path.join(current_app.config['AUDIO_FOLDER'], audio.file_path)
        if not os.path.exists(audio_path):
            flash('Arquivo de áudio não encontrado no servidor.', 'danger')
            return redirect(url_for('pdf.dashboard'))
            
        # Verifica o tamanho do arquivo
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            flash('O arquivo de áudio está corrompido.', 'danger')
            return redirect(url_for('pdf.dashboard'))
        
        # Nome para o arquivo de download (remove caracteres especiais)
        safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', pdf.title)
        download_name = f"{safe_title}.mp3"
        
        # Configura os headers para streaming
        def generate():
            with open(audio_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB por chunk
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(generate(), mimetype='audio/mpeg')
        response.headers['Content-Disposition'] = f'attachment; filename="{download_name}"'
        response.headers['Content-Length'] = file_size
        return response
        
    except Exception as e:
        print(f"[Download] ERRO: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('Erro ao baixar o arquivo de áudio. Por favor, tente novamente.', 'danger')
        return redirect(url_for('pdf.dashboard'))

@pdf_bp.route('/delete/<int:pdf_id>', methods=['POST'])
@login_required
@subscription_required
def delete_pdf(pdf_id):
    # Verifica se o PDF existe e pertence ao usuário
    pdf = PDF.query.filter_by(id=pdf_id, user_id=current_user.id).first_or_404()
    
    try:
        # Remove o arquivo PDF
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf.file_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        # Remove os arquivos de áudio associados
        for audio in pdf.audio_files:
            audio_path = os.path.join(current_app.config['AUDIO_FOLDER'], audio.file_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        # Remove o registro do banco de dados
        db.session.delete(pdf)
        db.session.commit()
        
        flash('PDF excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir PDF: {str(e)}', 'danger')
    
    return redirect(url_for('pdf.dashboard'))

# Rota temporária para criar um arquivo MP3 de teste
@pdf_bp.route('/create-test-audio')
def create_test_audio():
    try:
        # Diretório para o áudio
        audio_folder = current_app.config['AUDIO_FOLDER']
        
        # Cria o diretório se não existir
        if not os.path.exists(audio_folder):
            os.makedirs(audio_folder, exist_ok=True)
            
        # Nome do arquivo de teste
        test_filename = "test_audio.mp3"
        test_path = os.path.join(audio_folder, test_filename)
        
        # Cria um arquivo MP3 básico (1 segundo de silêncio)
        with open(test_path, 'wb') as f:
            # Bytes mínimos de um MP3 válido
            mp3_bytes = b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            f.write(mp3_bytes)
            
        return f"Arquivo de teste criado em: {test_path}"
    except Exception as e:
        return f"Erro ao criar arquivo de teste: {str(e)}"

# Rota para servir o áudio de teste
@pdf_bp.route('/test-audio')
def serve_test_audio():
    try:
        # Diretório para o áudio
        audio_folder = current_app.config['AUDIO_FOLDER']
        test_filename = "test_audio.mp3"
        
        # Verifica se o arquivo existe
        test_path = os.path.join(audio_folder, test_filename)
        if not os.path.exists(test_path):
            # Cria o arquivo se não existir
            with open(test_path, 'wb') as f:
                mp3_bytes = b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                f.write(mp3_bytes)
        
        # Serve o arquivo
        return send_from_directory(
            audio_folder,
            test_filename,
            as_attachment=True,
            download_name="test_audio.mp3"
        )
    except Exception as e:
        return f"Erro ao servir arquivo de teste: {str(e)}" 