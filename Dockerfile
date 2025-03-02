FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema necessárias para psycopg2 e Playwright
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright e o navegador Chromium
RUN python -m playwright install chromium --with-deps

# Copiar o resto do código
COPY . .

# Tornar o script de entrypoint executável
RUN chmod +x entrypoint.sh

# Configurar entrypoint
ENTRYPOINT ["./entrypoint.sh"]