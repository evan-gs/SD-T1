# Escolha uma imagem base que contenha o Python na versão desejada
FROM python:3.11

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copie o arquivo de dependências para dentro do contêiner
COPY requirements.txt .

# Instale as dependências listadas no arquivo
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante dos arquivos da aplicação para o diretório de trabalho
COPY . .

# Indique a porta que a aplicação irá utilizar
EXPOSE 5000

# Defina o comando que será executado ao iniciar o contêiner
CMD ["python", "app.py"]
