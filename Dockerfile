
# Usar imagem oficial do Python leve
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependências do sistema necessárias para mysqlclient e outros
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    python3-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar o projeto
COPY . /app/

# Coletar estáticos (será executado no entrypoint ou build se DB não for necessário aqui)
# Para build seguro, rodamos collectstatic sem input
# Nota: Isso pode falhar se o collectstatic depender do DB, mas com whitenoise geralmente é ok se configurado certo.
# Se falhar, movemos para o entrypoint.

# Criar script de entrypoint para aguardar DB e rodar migrações
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expor a porta 8000 (Gunicorn roda aqui)
EXPOSE 8000

# Comando padrão
ENTRYPOINT ["/app/entrypoint.sh"]
