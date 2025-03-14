from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models.db import db
from app.models.pdf import PDF, AudioFile
from app.utils.forms import UploadPDFForm
from app.utils.pdf_processor import save_pdf_file, extract_text_from_pdf
from app.utils.tts_service import text_to_speech
import os
import threading

pdf_bp = Blueprint('pdf', __name__)

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
def dashboard():
    # Log para depuração
    print(f"[Dashboard] Usuário {current_user.email} tentando acessar o dashboard")
    print(f"[Dashboard] Status da assinatura: {current_user.subscription_status}")
    print(f"[Dashboard] Data de término: {current_user.subscription_end_date}")
    
    # Força o acesso temporariamente para depuração
    # Se o usuário estiver autenticado, permitimos o acesso ao dashboard
    print(f"[Dashboard] Permitindo acesso ao dashboard para usuário {current_user.email}")
    
    pdfs = PDF.query.filter_by(user_id=current_user.id).order_by(PDF.upload_date.desc()).all()
    form = UploadPDFForm()
    
    return render_template('dashboard.html', pdfs=pdfs, form=form)

@pdf_bp.route('/upload', methods=['POST'])
@login_required
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

@pdf_bp.route('/convert/<int:pdf_id>')
@login_required
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
            
        # Verifica se já está em processamento
        if pdf.is_processing:
            print(f"[Convert] PDF já está em processamento")
            flash('Este PDF já está sendo convertido. Por favor, aguarde.', 'info')
            return redirect(url_for('pdf.dashboard'))
        
        # Marca o PDF como em processamento
        pdf.is_processing = True
        db.session.commit()
        
        # Inicia a thread de conversão em segundo plano
        print(f"[Convert] Iniciando conversão em segundo plano para PDF: {pdf.title}")
        conversion_thread = threading.Thread(
            target=process_conversion_background,
            args=(pdf_id, current_user.id, current_app._get_current_object())
        )
        conversion_thread.daemon = True
        conversion_thread.start()
        
        # Informa ao usuário que a conversão foi iniciada
        flash('A conversão para áudio foi iniciada em segundo plano. Aguarde alguns instantes e atualize a página para verificar quando estiver pronto.', 'info')
        return redirect(url_for('pdf.dashboard'))
    
    except Exception as e:
        print(f"[Convert] ERRO ao iniciar conversão: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash(f'Não foi possível iniciar a conversão: {str(e)}', 'danger')
        return redirect(url_for('pdf.dashboard'))

@pdf_bp.route('/download/<int:pdf_id>')
@login_required
def download_audio(pdf_id):
    # Log para depuração
    print(f"[Download] Usuário {current_user.email} tentando baixar áudio do PDF {pdf_id}")
    
    # Verifica se o PDF existe e pertence ao usuário
    pdf = PDF.query.filter_by(id=pdf_id, user_id=current_user.id).first_or_404()
    
    # Verifica se existe um áudio para este PDF
    if not pdf.audio_files:
        flash('Este PDF ainda não foi convertido para áudio.', 'warning')
        return redirect(url_for('pdf.dashboard'))
    
    # Obtém o primeiro arquivo de áudio (poderia ser expandido para múltiplos arquivos)
    audio = pdf.audio_files[0]
    
    # Nome para o arquivo de download
    download_name = f"{pdf.title.replace(' ', '_')}.mp3"
    
    return send_from_directory(
        current_app.config['AUDIO_FOLDER'],
        audio.file_path,
        as_attachment=True,
        download_name=download_name
    )

@pdf_bp.route('/delete/<int:pdf_id>', methods=['POST'])
@login_required
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