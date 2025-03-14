FROM python:3.9-slim

WORKDIR /app

# Instala as dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Cria diretórios necessários
RUN mkdir -p app/static/uploads app/static/audios

# Expõe a porta que a aplicação usará
EXPOSE 8000

# Define a variável de ambiente para produção
ENV FLASK_ENV=production
# Configura o PYTHONPATH para incluir o diretório atual
ENV PYTHONPATH=/app

# Comando para iniciar a aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"] 