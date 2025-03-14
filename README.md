# AI Reader - Transforme PDFs em Áudio

AI Reader é uma aplicação web que permite aos usuários fazer upload de livros em PDF e convertê-los em arquivos de áudio MP3 usando a avançada tecnologia de Text-to-Speech da OpenAI.

## Recursos

- 🔒 Sistema de autenticação (login/registro)
- 💳 Integração com Stripe para pagamentos de assinatura mensal
- 📚 Upload e gerenciamento de PDFs
- 🔊 Conversão de PDFs em arquivos de áudio MP3
- ⬇️ Download de arquivos de áudio
- 📱 Interface responsiva e amigável

## Configuração

### Pré-requisitos

- Python 3.8 ou superior (para execução local)
- Pip (gerenciador de pacotes Python)
- Conta no Stripe para processamento de pagamentos
- Chave de API da OpenAI
- Docker e Docker Compose (para execução com Docker)

### Instalação e Execução

#### Com Docker (Recomendado)

1. Clone o repositório:
```
git clone https://github.com/seu-usuario/aireader.git
cd aireader
```

2. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
```
SECRET_KEY=sua_chave_secreta
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_PRICE_ID=price_...
OPENAI_API_KEY=sk-...
```

3. Construa e inicie os contêineres:
```
docker-compose up -d
```

4. Acesse a aplicação em seu navegador:
```
http://localhost:8000
```

5. Para parar a aplicação:
```
docker-compose down
```

#### Localmente (Sem Docker)

1. Clone o repositório:
```
git clone https://github.com/seu-usuario/aireader.git
cd aireader
```

2. Crie e ative um ambiente virtual:
```
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```
pip install -r requirements.txt
```

4. Crie um arquivo `.env` na raiz do projeto com as variáveis necessárias (veja acima).

5. Inicie a aplicação:
```
python main.py
```

6. Acesse a aplicação em seu navegador:
```
http://localhost:8000
```

### Solução de problemas

Se você encontrar erros relacionados a importações ou módulos não encontrados, verifique:

1. Se os arquivos `__init__.py` existem nos seguintes diretórios:
   - `app/`
   - `app/controllers/`
   - `app/models/`
   - `app/utils/`

2. Se você está usando a estrutura de importação correta:
   - Para importações dentro do pacote: `from app.models.user import User`
   - Ao executar o aplicativo: `python main.py`

3. Se o PYTHONPATH está configurado corretamente (para Docker):
   - Deve conter o diretório raiz do projeto

## Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Banco de Dados**: SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Processamento de Pagamentos**: Stripe
- **Text-to-Speech**: OpenAI
- **Processamento de PDF**: PDFPlumber
- **Containerização**: Docker e Docker Compose

## Estrutura do Projeto

```
aireader/
│
├── app/                    # Código principal da aplicação
│   ├── __init__.py         # Inicializa o aplicativo Flask
│   ├── controllers/        # Controladores
│   │   └── __init__.py     # Torna o diretório um pacote Python
│   ├── models/             # Modelos de dados
│   │   └── __init__.py     # Torna o diretório um pacote Python
│   ├── static/             # Arquivos estáticos (CSS, JS)
│   │   ├── css/
│   │   ├── js/
│   │   ├── uploads/        # PDFs enviados
│   │   └── audios/         # Arquivos de áudio gerados
│   ├── templates/          # Templates HTML
│   └── utils/              # Utilitários e serviços
│       └── __init__.py     # Torna o diretório um pacote Python
│
├── main.py                 # Ponto de entrada da aplicação para execução local
├── requirements.txt        # Dependências do projeto
├── Dockerfile              # Configuração do Docker
├── docker-compose.yml      # Configuração do Docker Compose
└── README.md               # Documentação
```

## Modo de Uso

1. Crie uma conta ou faça login
2. Assine o plano mensal de R$100
3. Faça upload de um PDF
4. Clique em "Converter" para transformar o PDF em áudio
5. Quando a conversão estiver concluída, clique em "Baixar MP3"