const sessionid = uuid.v4();

function sendMessageToLex(message) {
    console.log("Mensagem enviada");
    displayUserMessage(message); // Exibe a mensagem do usuário antes de enviar
    fetch('http://localhost:5000/v1/lex', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message, sessionId: sessionid })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Resposta do Lex:', data);
        displayBotResponse(data.messages);
    })
    .catch(error => {
        console.error('Erro ao chamar o Lex:', error);
        displayBotResponse([{ content: 'Desculpe, não entendi. Poderia repetir?', contentType: 'PlainText' }]);
    });
}

function displayUserMessage(message) {
    var chatbox = document.getElementById('chatbox');
    chatbox.innerHTML += '<div class="user-message">' + message + '</div>';
}

function displayBotResponse(messages) {
    var chatbox = document.getElementById('chatbox');
    
    // Exibe cada mensagem retornada pelo Lex
    messages.forEach(function (message) {
        if (message.contentType === 'PlainText') {
            // Mensagem de texto simples do bot
            chatbox.innerHTML += `<div class="bot-message">${message.content}</div>`;
        } else if (message.contentType === 'ImageResponseCard') {
            // Exibe o cartão de resposta com imagem
            var card = message.imageResponseCard;
            var cardHTML = `
                <div class="card">
                    <h3>${card.title || 'Sem título'}</h3>
                    ${card.imageUrl ? `<img src="${card.imageUrl}" alt="Card Image">` : ''}
                    ${card.buttons ? card.buttons.map(button => `<button onclick="handleButtonClick('${button.value}')">${button.text}</button>`).join('') : ''}
                </div>
            `;
            chatbox.innerHTML += cardHTML;
        }
    });

    // Rola para o final do chat automaticamente após exibir a resposta
    chatbox.scrollTop = chatbox.scrollHeight;
}

// Função para lidar com cliques nos botões dos cartões
function handleButtonClick(value) {
    sendMessageToLex(value);  // Envia o valor do botão clicado como mensagem para o Lex
}


// Envio de áudio para o backend
async function transcribeAudio(audioBlob) {
    toggleLoading(true, "Transcrevendo áudio...");
    console.log("Áudio enviado");
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.webm');

    try {
        const response = await fetch('http://localhost:5000/sendAudio', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        console.log('Transcrição recebida:', data.job_transcript);
        
        sendMessageToLex(data.job_transcript);
    } catch (error) {
        console.error('Erro no processo de transcrição:', error);
    } finally {
        toggleLoading(false); // Finaliza o loading, independentemente do resultado
    }
}

let isRecording = false;  // Variável para controlar o estado da gravação
let mediaRecorder;
let audioChunks = [];

// Função para iniciar a gravação de áudio
function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        mediaRecorder.start();
        
        console.log('Gravação iniciada');
        
        // Mudar ícone para o quadrado (indicando que pode parar a gravação)
        const microphoneIcon = document.getElementById('microphoneIcon');
        microphoneIcon.classList.remove('fa-microphone');
        microphoneIcon.classList.add('fa-stop');
        microphoneIcon.classList.add('active');
    }).catch(error => {
        console.error('Erro ao acessar o microfone:', error);
    });
}

// Função para parar a gravação de áudio
function stopRecording() {
    return new Promise(resolve => {
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];
            
            console.log('Gravação parada');

            // Parar todas as tracks de áudio para liberar o microfone
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            // Mudar ícone de volta para o microfone
            const microphoneIcon = document.getElementById('microphoneIcon');
            microphoneIcon.classList.remove('fa-stop');
            microphoneIcon.classList.remove('active');
            microphoneIcon.classList.add('fa-microphone');
            
            resolve(audioBlob);
        };
        mediaRecorder.stop();
    });
}

// Função para exibir e ocultar o loading e desabilitar/ativar a interface
function toggleLoading(isLoading, textLoading=undefined) {
    const loading = document.getElementById('loading');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const microphoneIcon = document.getElementById('microphoneIcon');
    const imageIcon = document.getElementById('imageIcon');
    
    if (isLoading) {
        document.getElementById('text-loading').textContent = textLoading;
        loading.style.display = 'flex';
        userInput.disabled = true;
        sendButton.disabled = true;

        microphoneIcon.style.pointerEvents = 'none';
        microphoneIcon.style.color = 'red';

        imageIcon.style.pointerEvents = 'none';
        imageIcon.style.color = 'red';
    } else {
        loading.style.display = 'none';
        userInput.disabled = false;
        sendButton.disabled = false;

        microphoneIcon.style.pointerEvents = 'auto';
        microphoneIcon.style.color = '#333';
    }
}


// Enviar mensagem inicial automaticamente ao carregar a página
document.addEventListener('DOMContentLoaded', function() {
    var initialMessage = "Olá! Escreva uma saudação para começar nossa conversa.";

    const imageIcon = document.getElementById('imageIcon');
    imageIcon.style.pointerEvents = 'none';
    imageIcon.style.color = 'red';
    
    // Exibir a mensagem inicial do bot
    displayBotResponse([{ content: initialMessage, contentType: 'PlainText' }]);
});

document.getElementById('sendButton').addEventListener('click', function() {
    var userMessage = document.getElementById('userInput').value;
    var botMessage = document.getElementsByClassName('bot-message');
    var lastBotMessage = botMessage[botMessage.length - 1].innerHTML;
    console.log('mensagem do usuario: ', userMessage);
    console.log('mensagem do bot: ', lastBotMessage);

    if (
        (
          lastBotMessage.trim() === "Qual seu Telefone com DDD? (Envie apenas números)" ||
          lastBotMessage.trim() === "Número de Telefone inválido! Só é permitido a entrada de números." ||
          lastBotMessage.trim() === "Telefone inválido. Digite apenas números."
        ) 
        && !isNaN(userMessage)
        ) {
        const imageIcon = document.getElementById('imageIcon');
        const microphoneIcon = document.getElementById('microphoneIcon');
        microphoneIcon.style.pointerEvents = 'none';
        microphoneIcon.style.color = 'red';
        imageIcon.style.pointerEvents = 'auto';
        imageIcon.style.color = '#333';
        document.getElementById('userInput').value='';
        displayUserMessage(userMessage);
        displayBotResponse([{ content: "Envie a imagem do seu animal perdido.", contentType: 'PlainText' }]);

    } else if (userMessage.trim() !== "") {
        document.getElementById('userInput').value='';
        sendMessageToLex(userMessage);  // Chama a função para enviar a mensagem ao Lex
    } else {
        console.error("Mensagem está vazia.");
    }   
});

// Captura a tecla Enter e simula o clique no botão
document.getElementById('userInput').addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Evita quebra de linha no input
        document.getElementById("sendButton").click(); // Simula o clique
    }
});

// Escuta eventos de clique no contêiner "chatbox"
document.getElementById("chatbox").addEventListener("click", function(event) {
    // Verifica se o clique foi em um botão
    if (event.target.tagName === "BUTTON") {
        // Verifica se o botão está dentro de uma div com classe "card" que contém o texto antes de gerar o prompt do bedrock
        const cardElement = event.target.closest(".card");
        if (cardElement &&
            cardElement.querySelector("h3")?.textContent === "Você está pronto para este compromisso?" &&
            event.target.textContent.trim() === "sim") {
            
            console.log("Botão sim clicado antes do bedrock");
            toggleLoading(true, "");
            
            // Inicia a observação para detectar a próxima "bot-message" que aparece após o card
            const chatbox = document.getElementById("chatbox");
            const observer = new MutationObserver((mutationsList) => {
                for (const mutation of mutationsList) {
                    if (mutation.type === "childList") {
                        // Verifica se uma nova div com a classe "bot-message" foi adicionada
                        mutation.addedNodes.forEach((node) => {
                            if (node.classList?.contains("bot-message")) {
                                console.log("Bot message detectada após o card, desativando loading...");
                                toggleLoading(false);
                                observer.disconnect(); // Para o observer após detectar a div específica
                            }
                        });
                    }
                }
            });

            // Inicia a observação de mudanças nos filhos de "chatbox"
            observer.observe(chatbox, { childList: true, subtree: true });
        }
    }
});


document.getElementById('microphoneIcon').addEventListener('click', function () {
    if (!isRecording) {
        startRecording();
        isRecording = true;
    } else {
        stopRecording().then(audioBlob => {
            transcribeAudio(audioBlob);  // Envia o áudio para transcrição e Lex
            isRecording = false;
        });
    }
});


/* Envio de imagem */

// Função para exibir a imagem do usuário no chatbox
function displayUserImage(imageSrc) {
    var chatbox = document.getElementById('chatbox');
    chatbox.innerHTML += `<div class="user-message"><img src="${imageSrc}" alt="User Image" style="max-width: 100px; max-height: 100px;"></div>`;
}

// Função para enviar imagens ao S3 e retornar analise Rekognition
async function uploadImageToS3(file) {
    toggleLoading(true, "Processando imagem...");
    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch('http://localhost:5000/uploadImage', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        const full_data = data.full_data;
        
        console.log('Todos os dados retornados do Rekognition:', full_data);

        console.log('informações do pet do dynamodb', full_data.informacoes[0]['data_de_chegada'])

        // Função para formatar a data no formato dia/mes/ano
        const formatarData = (dataStr) => {
            if (!dataStr) return "N/A";
            const [ano, dia, mes] = dataStr.split("-");
            return `${dia}/${mes}/${ano}`;
        };

        // Mensagens iniciais para o tipo e raça do pet
        const responses = [
            { content: `Tipo do pet: ${full_data.tipoPet}`, contentType: 'PlainText' },
            { content: `Raça do pet: ${full_data.racaPet}`, contentType: 'PlainText' }
        ];

        // Verifica se `informacoes` existe e é um array antes de iterar sobre ele
        if (Array.isArray(full_data.informacoes) && full_data.informacoes.length > 0) {
            responses.push({ content: `Animais perdidos encontrados no banco:`, contentType: 'PlainText' });
            
            full_data.informacoes.forEach(info => {
                const dataFormatada = formatarData(info.data_de_chegada);
                const message = `Categoria: ${info.categoria || "N/A"} <br> Raça: ${info.raca || "N/A"} <br> Data de Chegada: ${dataFormatada} <br> <a href="${info.links3 || 'N/A'}" target="_blank"> Imagem do Pet </a>`;
                responses.push(
                    { content: message, contentType: 'PlainText' },
                    { content: "Caso algum animal descrito acima seja parecido com o seu, contate-nos através desse número para analisarmos o seu caso:<br> (11) 98457-3057", contentType: 'PlainText' }
                );
            });
        } else {
            // Mensagem caso não haja informações de animais no DynamoDB
            responses.push({ content: "Nenhum animal encontrado no banco de dados dos animais perdidos.", contentType: 'PlainText' });
        }

        // Exibir a mensagem do resultado da análise Rekognition no chatbox
        displayBotResponse(responses);

    } catch (error) {
        console.error('Erro ao enviar a imagem:', error);
    } finally {
        toggleLoading(false); // Finaliza o loading, independentemente do resultado
    }
}

// Exibir a imagem no chatbox e enviar para o S3
document.getElementById('imageUpload').addEventListener('change', function (event) {
    const file = event.target.files[0];
    if (file && (file.type === 'image/jpeg' || file.type === 'image/png')) {
        const reader = new FileReader();
        
        // Exibe a imagem no chatbox
        reader.onload = function (e) {
            displayUserImage(e.target.result); // Exibe a imagem localmente
        };
        reader.readAsDataURL(file);
        
        // Envia o arquivo ao S3
        uploadImageToS3(file);

    } else {
        alert('Formato de imagem inválido. Por favor, selecione uma imagem .jpg ou .png.');
        event.target.value = ''; // Limpa o input de arquivo para forçar nova seleção
    }
});
