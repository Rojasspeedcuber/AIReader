import os
import uuid
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
    # Inicializa o cliente da OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Gera um nome de arquivo único
    unique_filename = f"{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(output_folder, unique_filename)
    
    try:
        # Utiliza um arquivo temporário para evitar problemas de permissão
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            # Faz a chamada para a API
            response = client.audio.speech.create(
                model="tts-1",  # ou "tts-1-hd" para melhor qualidade
                voice="alloy",  # opções: alloy, echo, fable, onyx, nova, shimmer
                input=text,
                response_format="mp3"
            )
            
            # Salva a resposta no arquivo temporário
            response.stream_to_file(temp_file.name)
            
            # Move o arquivo temporário para o destino final
            import shutil
            shutil.move(temp_file.name, output_path)
        
        # Estima a duração (aproximadamente)
        # Em média, a fala humana tem cerca de 150 palavras por minuto
        word_count = len(text.split())
        estimated_duration = (word_count / 150) * 60  # em segundos
        
        return unique_filename, estimated_duration
    
    except Exception as e:
        print(f"Erro na conversão de texto para fala: {e}")
        return None, 0 