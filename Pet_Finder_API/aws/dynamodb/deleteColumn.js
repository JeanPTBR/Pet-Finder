const AWS = require('aws-sdk');
AWS.config.update({ region: 'us-east-1' }); // Defina a região apropriada
const dynamoDb = new AWS.DynamoDB.DocumentClient();

// IDs dos itens que você deseja atualizar
const petIds = [
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  // Adicione os outros IDs aqui
];

const removeColumn = async (id) => {
  const params = {
    TableName: "AnimaisInstituicao",
    Key: { id: id },
    UpdateExpression: "REMOVE nome" // Expressão para remover a coluna nome_pet
  };

  try {
    await dynamoDb.update(params).promise();
    console.log(`Coluna 'nome_pet' removida do item com id: ${id}`);
  } catch (error) {
    console.error(`Erro ao remover a coluna 'nome_pet' do item ${id}:`, error);
  }
};

const removeColumnFromAllItems = async () => {
  for (const id of petIds) {
    await removeColumn(id);
  }
  console.log("Coluna 'nome_pet' removida de todos os itens!");
};

removeColumnFromAllItems();
