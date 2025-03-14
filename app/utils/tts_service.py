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
    
    # Inicializa o cliente da OpenAI
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        print(f"[TTS] Inicializando cliente OpenAI com API key: {api_key[:5]}...{api_key[-4:] if api_key else 'None'}")
        client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"[TTS] ERRO ao inicializar cliente OpenAI: {e}")
        return None, 0
    
    # Gera um nome de arquivo único
    unique_filename = f"{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(output_folder, unique_filename)
    print(f"[TTS] Nome do arquivo de saída: {unique_filename}")
    print(f"[TTS] Caminho completo: {output_path}")
    
    try:
        print(f"[TTS] Criando arquivo temporário para armazenar o áudio")
        # Utiliza um arquivo temporário para evitar problemas de permissão
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name
            print(f"[TTS] Arquivo temporário criado em: {temp_path}")
            
            print(f"[TTS] Chamando API da OpenAI para conversão de texto para fala")
            start_time = time.time()
            
            # Faz a chamada para a API
            response = client.audio.speech.create(
                model="tts-1",  # ou "tts-1-hd" para melhor qualidade
                voice="alloy",  # opções: alloy, echo, fable, onyx, nova, shimmer
                input=text,
                response_format="mp3"
            )
            
            api_time = time.time() - start_time
            print(f"[TTS] Resposta da API recebida em {api_time:.2f} segundos")
            
            # Salva a resposta no arquivo temporário
            print(f"[TTS] Salvando a resposta no arquivo temporário")
            response.stream_to_file(temp_path)
            print(f"[TTS] Arquivo temporário salvo com sucesso")
            
            # Move o arquivo temporário para o destino final
            print(f"[TTS] Movendo arquivo temporário para o destino final")
            import shutil
            shutil.move(temp_path, output_path)
            print(f"[TTS] Arquivo movido com sucesso para: {output_path}")
        
        # Estima a duração (aproximadamente)
        # Em média, a fala humana tem cerca de 150 palavras por minuto
        word_count = len(text.split())
        estimated_duration = (word_count / 150) * 60  # em segundos
        print(f"[TTS] Conversão concluída. Duração estimada: {estimated_duration:.2f} segundos")
        
        return unique_filename, estimated_duration
    
    except Exception as e:
        print(f"[TTS] ERRO na conversão de texto para fala: {e}")
        import traceback
        print(traceback.format_exc())
        
        # Limpa os arquivos temporários em caso de erro
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                print(f"[TTS] Removendo arquivo temporário após erro")
                os.remove(temp_path)
        except:
            pass
        
        return None, 0 