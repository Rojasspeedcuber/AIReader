from app import app
import os

if __name__ == '__main__':
    # Cria diretórios necessários, caso não existam
    os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, 'audios'), exist_ok=True)
    
    # Obtém a porta do ambiente ou usa 8000 como padrão
    port = int(os.environ.get('PORT', 8000))
    
    # Inicia a aplicação
    app.run(debug=False, host='0.0.0.0', port=port) 