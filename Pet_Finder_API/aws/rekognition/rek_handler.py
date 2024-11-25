import os
import json
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Configuração dos serviços AWS
rekognition = boto3.client('rekognition', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
translate = boto3.client('translate', region_name='us-east-1')

BUCKET_NAME = os.environ['S3_BUCKET']
TABLE_NAME = 'AnimaisInstituicao'

# Raças definidas
racas_dogs = ['bulldog', 'Labrador Retriever', 'poodle', 'beagle', 'German Shepherd']
racas_cats = ['siamese', 'persian', 'maine coon']
racas_exoticos = ['iguana', 'cobra', 'tartaruga']
racas_passaros = ['canário', 'papagaio', 'periquito']

def traduzir_raca(raca):
    try:
        response = translate.translate_text(
            Text=raca,
            SourceLanguageCode="en",
            TargetLanguageCode="pt"
        )
        return response.get('TranslatedText', raca)
    except Exception as e:
        print("Erro ao traduzir raca:", e)
        return raca

def identificar_pet(labels):
    categoria_pet = 'Desconhecido'
    raca_pet = 'Desconhecida'

    for label in labels:
        if label['Name'] in ['Dog', 'Canine']:
            categoria_pet = 'Cachorro'
            for raca in racas_dogs:
                if any(l['Name'].lower() == raca.lower() for l in labels):
                    raca_pet = raca
            if any(l['Name'] == 'German Shepherd' for l in labels):
                raca_pet = 'Pastor Alemão'
        elif label['Name'] == 'Cat':
            categoria_pet = 'Gato'
            for raca in racas_cats:
                if any(l['Name'].lower() == raca.lower() for l in labels):
                    raca_pet = raca
        elif label['Name'] == 'Bird':
            categoria_pet = 'Pássaros'
            for l in labels:
                raca_traduzida = traduzir_raca(l['Name'])
                if raca_traduzida in racas_passaros:
                    raca_pet = raca_traduzida
        elif label['Name'] in ['Iguana', 'Lizard', 'Reptile']:
            categoria_pet = 'Exóticos'
            for raca in racas_exoticos:
                if any(l['Name'].lower() == raca.lower() for l in labels):
                    raca_pet = raca
        elif label['Name'] == 'Ferret':
            categoria_pet = 'Exóticos'
            raca_pet = 'Furão'

    return {'categoriaPet': categoria_pet, 'racaPet': raca_pet}

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        filename = body["image_name"]

        print("Body recebido:", body)
        print("Chave 'image_name':", body.get("image_name"))

    except KeyError:
        return {
            "statusCode": 400, "body": json.dumps({"error": "image_name is required in the request body."}),
            "headers": {"Content-Type": "application/json"}
            }

    try:
        rekognition_response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': f'imgs/{filename}'}},
            MaxLabels=30,
            MinConfidence=85
        )
    except ClientError as error:
        return {
            "statusCode": 500, "body": json.dumps({'error': str(error)}),
            "headers": {"Content-Type": "application/json"}
            }

    labels = rekognition_response['Labels']
    print("Labels detectadas pelo Rekognition:", labels)

    pet_info = identificar_pet(labels)
    categoria_pet = pet_info['categoriaPet']
    raca_pet = pet_info['racaPet']

    if categoria_pet == 'Desconhecido':
        return {
            "statusCode": 400, "body": json.dumps({"error": "Não foi possível identificar o tipo de pet."}),
            "headers": {"Content-Type": "application/json"}
            }

    table = dynamodb.Table(TABLE_NAME)
    filter_expression = {'categoria': categoria_pet}
    if raca_pet != 'Desconhecida':
        filter_expression['raca'] = raca_pet

    dynamo_response = table.scan(
        FilterExpression="categoria = :categoriaPet AND raca = :racaPet",
        ExpressionAttributeValues={
            ':categoriaPet': categoria_pet,
            ':racaPet': raca_pet
        }
    )
    dynamo_data = dynamo_response.get('Items', [])
    print("Dados encontrados no DynamoDB:", dynamo_data)

    response_data = {
        "tipoPet": categoria_pet,
        "racaPet": raca_pet,
        "informacoes": dynamo_data if dynamo_data else "Nenhuma informação encontrada."
    }
    
    return {
        "statusCode": 200,
        "body": json.dumps(response_data),
        "headers": {"Content-Type": "application/json"}
    }
