import json
import boto3
import urllib3
import re


# Inicializa o gerenciador de conexões do urllib3
http = urllib3.PoolManager()

FILTER_BREED_API = "https://qhewtd1shl.execute-api.us-east-1.amazonaws.com/v1/filter-breed"

# Função para buscar raças filtradas da tabela "AnimaisAdocao" do DynamoDB
def filtrar_racas_adocao(racas):
    
    def format_breeds(breeds_string):
        # Divide a string em uma lista com base em vírgulas e novas linhas
        breeds = re.split(r',|\n', breeds_string)
        # Remove números e pontos no início de cada item e limpa espaços extras
        breeds = [re.sub(r'^\d+\.\s*', '', breed.strip().lower()) for breed in breeds if breed.strip()]
        # Junta os itens formatados em uma única string, separados por vírgulas
        formatted_string = ', '.join(breeds)
        return formatted_string
    
    racas_formatadas = format_breeds(racas)
    
    payload = json.dumps({"breed": racas_formatadas})
    try:
        response = http.request(
            'POST',
            FILTER_BREED_API,
            body=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status == 200:
            data = json.loads(response.data.decode('utf-8'))
            print('raca enviada para a api: ', racas)
            print('dados retornados pela api: ', data)

            # Extrair apenas os campos desejados
            pets_filtered = [
                {
                    "id": pet["id"],
                    "nome": pet["nome"],
                    "raca": pet["raca"],
                    "link": pet["links3"]
                }
                for pet in data.get("pets", [])
            ]
            
            return pets_filtered
        
        else:
            print("Houve um problema na API de filtrar raças de adoção.")
            return None
    except Exception as e:
        print(f"Erro na chamada da API: {str(e)}")
        return None

class BedrockClient:
    @staticmethod
    def client():
        """Cria um cliente Bedrock Runtime na região especificada."""
        return boto3.client("bedrock-runtime", region_name="us-east-1")

    @staticmethod
    def generate_pet_suggestions(dados: dict):
        # Gera sugestões de raças para adoção usando o cliente Bedrock.
        user_message = (
            f"Baseado nas informações a seguir, sugira raças de animais para adoção:\n"
            f"Nome: {dados.get('nome')}\n"
            f"Idade do dono: {dados.get('idade')}\n"
            f"Tipo de moradia: {dados.get('moradia')}\n"
            f"Quintal: {dados.get('quintal')}\n"
            f"Alergias: {dados.get('alergia')}\n"
            f"Preferência de tipo de animal: {dados.get('tipo_animal')}\n"
            "As sugestões devem considerar espaço, alergias e tamanho do animal."
        )

        print("Mensagem do usuário para Bedrock:", user_message)

        try:
            # Enviar a mensagem ao modelo com o novo formato
            response = BedrockClient.client().invoke_model(
                modelId="amazon.titan-text-lite-v1",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "inputText": user_message,
                    "textGenerationConfig": {
                        "maxTokenCount": 4096,
                        "stopSequences": [],
                        "temperature": 0,
                        "topP": 1
                    }
                })
            )

            print("Resposta do Bedrock:", response)

            # Verifique o código de status da resposta
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                response_body = response['body'].read().decode('utf-8')
                response_json = json.loads(response_body)

                print("Corpo da resposta decodificado:", response_json)

                # Extrair o texto gerado de 'results' -> 'outputText'
                if response_json.get('results'):
                    suggestions = response_json['results'][0].get('outputText', "")
                    return suggestions.strip()
                else:
                    return None  # Retorna None se não houver sugestões
            else:
                return None  # Retorna None se a resposta não for bem-sucedida

        except Exception as e:
            print("Erro ao chamar o modelo Bedrock:", e)
            return None


class DynamoDBClient:
    @staticmethod
    def client():
        """Cria um cliente DynamoDB na região especificada."""
        return boto3.client("dynamodb", region_name="us-east-1")

    @staticmethod
    def search_pets_by_breed(breed):
        """Consulta a tabela AnimaisAdocao para buscar pets pela raça sugerida."""
        try:
            print("Consultando pets pela raça:", breed)  # Log da raça que está sendo consultada
            
            # Faz uma consulta na tabela
            response = DynamoDBClient.client().scan(
                TableName="AnimaisAdocao",
                FilterExpression="raca = :raca",  # Use o nome correto do atributo
                ExpressionAttributeValues={
                    ":raca": {"S": breed}
                }
            )
            
            # Verifica se houve resultados
            if 'Items' in response and response['Items']:
                pets = response['Items']
                print("Resposta do DynamoDB:", pets)  # Log da resposta do DynamoDB
                # Retorna uma lista com id, nome e link dos pets encontrados
                return [{
                    "id": pet["id"]["S"],
                    "nome": pet["nome"]["S"],
                    "link": pet["link"]["S"]
                } for pet in pets]
            else:
                print("Nenhum pet encontrado para a raça:", breed)
                return []
        
        except Exception as e:
            print("Erro ao consultar DynamoDB:", e)
            return []

# Função Lambda principal
def lambda_handler(event, context):
    session_attributes = event.get("sessionState", {}).get("sessionAttributes", {})
    intent_name = event['sessionState']['intent']['name']
    slots = event['sessionState']['intent']['slots']
    pet_list_message = 'Infelizmente, não encontramos pets disponíveis para adoção com as raças sugeridas.'

    # Inicializa dados como um dicionário vazio
    dados = {}

    if intent_name == "Adocao":
        # Coletando dados e validando
        try:
            def get_slot_value(slots, slot_name):
                slot = slots.get(slot_name)
                if slot and 'value' in slot and 'interpretedValue' in slot['value']:
                    return slot['value']['interpretedValue']
                return ""

            dados = {
                "nome": get_slot_value(slots, 'nome'),
                "idade": get_slot_value(slots, 'idade'),
                "tipo_animal": get_slot_value(slots, 'tipo'),
                "moradia": get_slot_value(slots, 'moradia'),
                "quintal": get_slot_value(slots, 'quintal'),
                "alergia": get_slot_value(slots, 'alergia'),
                "telefone": get_slot_value(slots, 'telefone'),
                "tempo": get_slot_value(slots, 'tempo'),
                "valores": get_slot_value(slots, 'valores')
            }

            print("Dados coletados para adoção:", dados)  # Print de verificação

            # Verifica se os campos obrigatórios estão preenchidos
            if not all([dados.get("nome"), dados.get("idade"), dados.get("moradia")]):
                return {
                    "sessionState": {
                        "dialogAction": {
                            "type": "Close"
                        },
                        "intent": {
                            "name": intent_name,
                            "state": "Failed"
                        },
                        "sessionAttributes": session_attributes
                    },
                    "messages": [
                        {
                            "contentType": "PlainText",
                            "content": "Por favor, forneça o nome, idade e tipo de moradia."
                        }
                    ]
                }
            
            elif dados.get('valores').lower() == "não" or dados.get('tempo').lower() == "não":
                return {
                    "sessionState": {
                        "dialogAction": {
                            "type": "Close"
                        },
                        "intent": {
                            "name": intent_name,
                            "state": "Fulfilled"
                        },
                        "sessionAttributes": session_attributes
                    },
                    "messages": [
                        {
                            "contentType": "PlainText",
                            "content": """Ficamos muito felizes pelo seu desejo de acolher um de nossos animais. <br>
                            No entanto, com base nas informações fornecidas, acreditamos que essa adoção talvez não seja ideal neste momento."""
                        },
                        {
                            "contentType": "PlainText",
                            "content": "Nosso compromisso é garantir que cada pet encontre um lar que atenda plenamente suas necessidades."
                        }
                    ],
                    "data": json.dumps(dados)
                }

            # Chama a função para obter sugestões de raças com base nos dados fornecidos
            pet_suggestions = BedrockClient.generate_pet_suggestions(dados)
            
            # Verifica se houve um erro ao gerar as sugestões de pets
            if pet_suggestions is None:
                response_message = "Desculpe, ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde."
                pet_list_message = ""  # Limpa qualquer mensagem adicional sobre pets
            
                return {
                    "sessionState": {
                        "dialogAction": {
                            "type": "Close"
                        },
                        "intent": {
                            "name": intent_name,
                            "state": "Failed"
                        },
                        "sessionAttributes": session_attributes
                    },
                    "messages": [
                        {
                            "contentType": "PlainText",
                            "content": response_message
                        }
                    ],
                    "data": json.dumps(dados)
                }


            print("Sugestões de pets geradas:", pet_suggestions)  # Print de verificação

            # Aqui estamos assumindo que as sugestões de raças são uma lista de raças separadas por vírgula.
            suggested_breeds = pet_suggestions.split(",")
            print('suggested breeds: ', suggested_breeds)
            found_pets = []

            for breed in suggested_breeds:
                # Remove espaços em branco e verifica se a raça não está vazia
                cleaned_breed = breed.strip()
                print('cleaned breed: ', type(cleaned_breed))
                if cleaned_breed:  # Verifica se a raça não está vazia
                    pets = filtrar_racas_adocao(cleaned_breed)
                    found_pets.extend(pets)
                    print('found pets: ', found_pets)

            if found_pets:
                # Criar uma mensagem com id, nome e link dos pets encontrados
                pet_list_message = "Além disso, encontramos alguns pets disponíveis para adoção que correspondem às raças sugeridas: <br><br>\n"
                for pet in found_pets:
                    pet_list_message += f"ID: {pet['id']} <br> Nome: {pet['nome']} <br> Raça: {pet['raca']} <br> <a href='{pet['link']}' target='_blank'> Imagem do Pet </a> <br><br>\n"
            else:
                pet_list_message = "Infelizmente, não encontramos pets disponíveis para adoção com as raças sugeridas."

            # Divide a string em linhas, removendo os números iniciais
            pet_suggestions_unformatted = [re.sub(r'^\d+\.\s*', '', breed.strip()) for breed in pet_suggestions.splitlines() if breed.strip()]
            # Adiciona numeração e insere a tag <br> no final de cada linha formatada
            pet_suggestions_formatted = [f"{i+1}. {breed} <br>" for i, breed in enumerate(pet_suggestions_unformatted)]
            # Junta todas as linhas em uma única string
            pet_suggestions_result = '\n'.join(pet_suggestions_formatted)
            # Cria a resposta personalizada
            response_message = f"Obrigado, {dados['nome']}! Estamos processando seu pedido de adoção. Aqui estão algumas sugestões de raças que podem se adequar ao seu perfil: <br> {pet_suggestions_result}"

        except Exception as e:
            print("Erro ao processar a solicitação de adoção:", e)  # Print de verificação
            response_message = "Ocorreu um erro ao processar sua solicitação."

    else:
        response_message = "Desculpe, estou aqui para ajudar com adoções e busca de pets perdidos."

    # Retorno JSON da função Lambda
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": intent_name,
                "state": "Fulfilled"
            },
            "sessionAttributes": session_attributes
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": response_message
            },
            {
                "contentType": "PlainText",
                "content": pet_list_message
            }
        ],
        "data": json.dumps(dados)
    }
