# Imagem base oficial leve do Python
FROM python:3.11-slim

# Evita criação de arquivos .pyc e força envio imediato de logs para o terminal
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Otimização de cache do Docker: instala dependências antes de copiar o código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação para a imagem
COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]