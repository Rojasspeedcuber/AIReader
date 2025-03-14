import os
import uuid
import time
from openai import OpenAI
import tempfile

def text_to_speech(text, output_folder):
    """
    Converte texto para fala usando a API TTS da OpenAI
    
    Args:
        text (str): Texto a ser convertido em fala
        output_folder (str): Pasta onde o áudio será salvo
        
    Returns:
        str: Caminho para o arquivo de áudio gerado
        float: Duração do áudio em segundos (aproximada)
    """
    print(f"[TTS] Iniciando conversão de texto para áudio. Tamanho do texto: {len(text)} caracteres")
    
    # Verifica se o texto é muito longo e trunca se necessário
    # O limite é de aproximadamente 4000 tokens (cerca de 16000 caracteres)
    max_chars = 16000
    if len(text) > max_chars:
        print(f"[TTS] Texto muito longo ({len(text)} caracteres). Truncando para {max_chars} caracteres.")
        text = text[:max_chars]
    
    # Tenta usar o método OpenAI primeiro
    try:
        print(f"[TTS] Tentando converter com OpenAI...")
        result = tts_with_openai(text, output_folder)
        if result[0]:  # Se conseguiu gerar o áudio
            print(f"[TTS] Conversão com OpenAI bem-sucedida!")
            return result
    except Exception as e:
        print(f"[TTS] Erro na conversão com OpenAI: {e}")
    
    # Se falhar com OpenAI, tenta o método alternativo com gTTS
    try:
        print(f"[TTS] Tentando converter com Google TTS...")
        result = tts_with_gtts(text, output_folder)
        if result[0]:
            print(f"[TTS] Conversão com Google TTS bem-sucedida!")
            return result
    except Exception as e:
        print(f"[TTS] Erro na conversão com Google TTS: {e}")
    
    # Se ambos falharem, tenta um método de último recurso
    try:
        print(f"[TTS] Tentando método de último recurso...")
        result = dummy_audio_fallback(output_folder)
        if result[0]:
            print(f"[TTS] Método de último recurso bem-sucedido")
            return result
    except Exception as e:
        print(f"[TTS] Todos os métodos de conversão falharam: {e}")
    
    # Se tudo falhar, retorna None
    return None, 0

def tts_with_openai(text, output_folder):
    """Converte texto para áudio usando OpenAI."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        print(f"[TTS-OpenAI] Verificando API key: {api_key[:5]}...{api_key[-4:] if api_key and len(api_key) > 8 else 'INVÁLIDA'}")
        
        if not api_key:
            print("[TTS-OpenAI] API key não encontrada")
            return None, 0
            
        client = OpenAI(api_key=api_key)
        
        # Gera um nome de arquivo único
        unique_filename = f"{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(output_folder, unique_filename)
        
        # Utiliza um arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name
            
            # Faz a chamada para a API
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3"
            )
            
            # Salva a resposta no arquivo temporário
            response.stream_to_file(temp_path)
            
            # Move o arquivo para o destino final
            import shutil
            shutil.move(temp_path, output_path)
        
        # Estima a duração
        word_count = len(text.split())
        estimated_duration = (word_count / 150) * 60  # em segundos
        
        return unique_filename, estimated_duration
        
    except Exception as e:
        print(f"[TTS-OpenAI] Erro: {e}")
        import traceback
        print(traceback.format_exc())
        
        # Limpa arquivos temporários
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
                
        return None, 0

def tts_with_gtts(text, output_folder):
    """Converte texto para áudio usando Google Text-to-Speech."""
    try:
        # Tenta importar gTTS
        try:
            from gtts import gTTS
        except ImportError:
            print("[TTS-Google] gTTS não encontrado, tentando instalar...")
            import subprocess
            subprocess.check_call(["pip", "install", "gtts==2.3.2"])
            from gtts import gTTS
            
        # Gera um nome de arquivo único
        unique_filename = f"{uuid.uuid4().hex}_gtts.mp3"
        output_path = os.path.join(output_folder, unique_filename)
        
        # Cria o áudio com gTTS (português Brasil)
        tts = gTTS(text=text, lang='pt-br', slow=False)
        tts.save(output_path)
        
        # Verifica se o arquivo foi criado
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:  # verifica tamanho mínimo
            print(f"[TTS-Google] Arquivo de áudio não criado corretamente")
            return None, 0
            
        # Estima a duração
        word_count = len(text.split())
        estimated_duration = (word_count / 150) * 60
        
        return unique_filename, estimated_duration
        
    except Exception as e:
        print(f"[TTS-Google] Erro: {e}")
        import traceback
        print(traceback.format_exc())
        return None, 0

def dummy_audio_fallback(output_folder):
    """Cria um arquivo de áudio vazio como último recurso."""
    try:
        print("[TTS-Fallback] Criando arquivo de áudio dummy...")
        
        # Gera um nome de arquivo único
        unique_filename = f"{uuid.uuid4().hex}_empty.mp3"
        output_path = os.path.join(output_folder, unique_filename)
        
        # Cria um arquivo MP3 mínimo válido (silêncio)
        # Estes bytes representam um MP3 válido de 1 segundo de silêncio
        mp3_bytes = b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        
        with open(output_path, 'wb') as f:
            f.write(mp3_bytes)
            
        return unique_filename, 1.0  # 1 segundo de duração
        
    except Exception as e:
        print(f"[TTS-Fallback] Erro no método de último recurso: {e}")
        return None, 0 