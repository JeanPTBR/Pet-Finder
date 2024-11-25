import subprocess
import boto3
import os
import re

# Variáveis
AWS_REGION = "us-east-1"
IMAGE_NAME = "jeanptbr/transcribe-lambda-public:latest"
PRIVATE_REPO_NAME = "transcribe-lambda-private"

# Obter o Account ID usando o boto3
sts_client = boto3.client("sts")
ACCOUNT_ID = sts_client.get_caller_identity()["Account"]
ECR_URI = f"{ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{PRIVATE_REPO_NAME}:latest"

# Função para executar comandos do terminal
def run_command(command, shell=False):
    result = subprocess.run(command, shell=shell, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Erro ao executar: {' '.join(command)}\n{result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, command)
    print(result.stdout)
    return result.stdout

# 1. Autenticar no ECR
print("Autenticando no ECR...")
login_command = f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com"
run_command(login_command, shell=True)

# 2. Criar repositório no ECR privado, se não existir
print("Verificando repositório no ECR...")
ecr_client = boto3.client("ecr", region_name=AWS_REGION)
try:
    ecr_client.describe_repositories(repositoryNames=[PRIVATE_REPO_NAME])
except ecr_client.exceptions.RepositoryNotFoundException:
    print("Repositório não encontrado. Criando repositório no ECR...")
    ecr_client.create_repository(repositoryName=PRIVATE_REPO_NAME)

# 3. Fazer o pull da imagem pública
print(f"Fazendo pull da imagem pública: {IMAGE_NAME}...")
run_command(["docker", "pull", IMAGE_NAME])

# 4. Tag da imagem para o ECR privado
print(f"Tagging da imagem para o ECR privado: {ECR_URI}...")
run_command(["docker", "tag", IMAGE_NAME, ECR_URI])

# 5. Fazer o push da imagem para o repositório ECR privado
print("Fazendo push da imagem para o ECR privado...")
run_command(["docker", "push", ECR_URI])

# 6. Atualizar o serverless.yml temporariamente para usar o ECR URI correto
print("Atualizando serverless.yml para usar o URI da imagem privada no ECR...")
serverless_path = "./Pet_Finder_API/serverless.yml"

# Ler o conteúdo do serverless.yml
with open(serverless_path, "r") as file:
    serverless_content = file.read()

# Substituir path: ./ por uri: ECR_URI
updated_content = re.sub(r"path: ./", f"uri: {ECR_URI}", serverless_content)

# Salvar o conteúdo atualizado
with open(serverless_path, "w") as file:
    file.write(updated_content)

print("Imagem atualizada e pronta para deploy com Serverless Framework.")
