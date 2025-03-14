# Este arquivo permite que o diretório 'app' seja importado como um pacote Python 

# Importa o aplicativo Flask do módulo principal
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa a aplicação Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_secreta_temporaria')

# Configura proteção CSRF
csrf = CSRFProtect(app)

# Configura o banco de dados SQLite
# Usando caminho absoluto para funcionar com Docker
db_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'instance', 'aireader.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['AUDIO_FOLDER'] = os.path.join(app.static_folder, 'audios')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Inicializa o banco de dados
from app.models.db import init_app
init_app(app)

# Configura o login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

from app.models.user import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Importa e registra os blueprints
from app.controllers.auth_controller import auth_bp
from app.controllers.pdf_controller import pdf_bp
from app.controllers.payment_controller import payment_bp

app.register_blueprint(auth_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(payment_bp)

# Rota principal
@app.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('auth.login')) 