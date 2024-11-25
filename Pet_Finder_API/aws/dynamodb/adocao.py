import json
import unicodedata
import boto3
from boto3.dynamodb.conditions import Attr


class DynamoDBClient:
    @staticmethod
    def client():
        """Cria um cliente DynamoDB na região especificada."""
        return boto3.resource("dynamodb", region_name="us-east-1")

    @staticmethod
    def search_pets_by_breed(breed):
        """Consulta a tabela AnimaisAdocao para buscar pets pela raça sugerida."""
        try:
            # Faz uma consulta na tabela
            table = DynamoDBClient.client().Table("AnimaisAdocao")
            response = table.scan(
                FilterExpression=Attr("raca_normalizada").contains(breed),  # Usando contains para capturar partes do texto
            )

            result = response.get('Items', [])
            
            return result
        
        except Exception as e:
            print("Erro ao consultar DynamoDB:", e)
            return []

# Função Lambda principal
def lambda_handler(event, context):
    def normalize_text(text):
        # Remove acentos e converte para minúsculas
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        ).strip().lower()
    
    try:
        body = json.loads(event['body'])
        breed_list = body["breed"].split(",")  # Dividir a string em uma lista de raças

    except KeyError:
        return {
            "statusCode": 400, "body": json.dumps({"error": "breed is required in the request body."}),
            "headers": {"Content-Type": "application/json"}
            }

    try:
        pets = []
        for breed in breed_list:
            cleaned_breed = normalize_text(breed)
            if cleaned_breed:  # Verifica se a raça não está vazia
                pets.extend(DynamoDBClient.search_pets_by_breed(cleaned_breed))

        response_data = {
            "pets": pets if pets else "Nenhum pet encontrado para as raças fornecidas."
        }

        return {
            "statusCode": 200,
            "body": json.dumps(response_data),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        print("Erro ao processar a solicitação de adoção:", e)  # Print de verificação
        response_message = f"Ocorreu um erro ao processar sua solicitação. {e}"
        return {
            "statusCode": 500,
            "body": json.dumps({"error": response_message}),
            "headers": {"Content-Type": "application/json"}
        }
