const express = require('express');

const {
    LexRuntimeV2
} = require('@aws-sdk/client-lex-runtime-v2');

const {
    Upload
} = require('@aws-sdk/lib-storage');

const {
    S3
} = require('@aws-sdk/client-s3');

const favicon = require('serve-favicon');

const multer = require('multer');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: './.env' }); // Para carregar variáveis de ambiente
console.log('botId: ', process.env.BOT_ID)
console.log('botAliasId: ', process.env.BOT_ALIAS_ID)
console.log('S3_BUCKET: ', process.env.S3_BUCKET)

const app = express();
app.use(express.json());

// Define a pasta 'public' como a pasta de arquivos estáticos
app.use(express.static(path.join(__dirname, 'public')));

const s3 = new S3({
    region: 'us-east-1'
});

const lexruntime = new LexRuntimeV2({
    region: 'us-east-1'
});

// Configuração para upload de áudio
const upload = multer({ dest: 'uploads/' });

// Define a rota para servir o index.html da pasta 'html'
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'html', 'index.html'));
  });

app.get('/adocao', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'html', 'adocao.html'));
  });

app.get('/encontrarPet', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'html', 'encontrarPet.html'));
  });

app.get('/chatbot', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'html', 'chatbot.html'));
  });


// Rota para transcrever o áudio usando AWS Transcribe
app.post('/sendAudio', upload.single('audio'), async (req, res) => {
    console.log('Transcrição solicitada');
    if (!req.file) {
        return res.status(400).json({ error: 'Arquivo de áudio não encontrado!' });
    }
    console.log('Arquivo recebido:', req.file);

    const audioPath = req.file.path;
    const bucketName = process.env.S3_BUCKET;
    const media_object_key = `audios/audio_${Date.now()}.webm`;

    // Primeiro, suba o arquivo para o S3
    const fileStream = fs.createReadStream(audioPath);
    const uploadParams = {
        Bucket: bucketName,
        Key: media_object_key,
        Body: fileStream,
        ContentType: 'audio/webm'
    };

    try {
        await new Upload({
            client: s3,
            params: uploadParams
        }).done();

        fs.unlinkSync(audioPath); // Apaga o arquivo local após o upload

        // Faz a chamada para API serverless para transcrever o áudio
        const response = await fetch('https://r7vwwh6fp7.execute-api.us-east-1.amazonaws.com/v1/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                media_object_key: media_object_key
            })
        });

        const data = await response.json();
        const transcript = data.job_transcript; 

        res.json({ job_transcript: transcript });

        // Deleta o áudio do S3 após enviar a transcrição para o usuário
        s3.deleteObject({
            Bucket: bucketName,
            Key: media_object_key
        }, (err, data) => {
            if (err) {
                console.error('Erro ao deletar o áudio do S3:', err);
            } else {
                console.log('Áudio deletado do S3 com sucesso.');
            }
        });
        
    } catch (error) {
        console.error('Erro ao fazer upload do arquivo:', error);
        res.status(500).json({ error: 'Erro ao fazer upload do arquivo' });
    }
});

// Rota para integrar o AWS Lex (reconhecer texto)
app.post('/v1/lex', (req, res) => {
    console.log('Rota Lex Solicitada');
    const { message, sessionId } = req.body;

    const botAliasId = process.env.BOT_ALIAS_ID;
    const botId = process.env.BOT_ID;

    const params = {
        botAliasId: botAliasId,  // Substitua pelo seu Alias ID do Lex no .env
        botId: botId,       // Substitua pelo seu Bot ID no .env
        localeId: 'pt_BR',
        sessionId: sessionId,
        text: message
    };

    lexruntime.recognizeText(params, function (err, data) {
        if (err) {
            console.error('Erro ao chamar o Lex:', err);
            res.status(500).json({ error: 'Erro ao chamar o Lex' });
        } else {
            res.json(data);
        }
    });
});

// Rota para upload de imagem no S3
app.post('/uploadImage', upload.single('image'), async (req, res) => {
    console.log('Upload de imagem solicitado');
    if (!req.file) {
        return res.status(400).json({ error: 'Arquivo de imagem não encontrado!' });
    }

    const imagePath = req.file.path;
    const bucketName = process.env.S3_BUCKET;
    const imageKey = `imgs/${Date.now()}_${req.file.originalname}`;

    // Faça upload da imagem para o S3
    const fileStream = fs.createReadStream(imagePath);
    const uploadParams = {
        Bucket: bucketName,
        Key: imageKey,
        Body: fileStream,
        ContentType: req.file.mimetype
    };

    try {
        await new Upload({
            client: s3,
            params: uploadParams
        }).done();

        fs.unlinkSync(imagePath); // Remove o arquivo local após o upload

        // Faz a chamada para API serverless para o rekognition
        const imageName = imageKey.split('/').pop();
        console.log('Nome da imagem:', imageName);
        const response = await fetch('https://r7vwwh6fp7.execute-api.us-east-1.amazonaws.com/v1/rekognition', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_name: imageName
            })
        });

        const data = await response.json();

        res.json({ full_data: data });

        // Deleta a imagem do S3 após o uso
        s3.deleteObject({
            Bucket: bucketName,
            Key: imageKey
        }, (err, data) => {
            if (err) {
                console.error('Erro ao deletar o áudio do S3:', err);
            } else {
                console.log('Imagem deletada do S3 com sucesso.');
            }
        });
    } catch (error) {
        console.error('Erro ao fazer upload da imagem:', error);
        res.status(500).json({ error: 'Erro ao fazer upload da imagem' });
    }
});

// Defina o caminho para o seu favicon
app.use(favicon(path.join(__dirname, 'public', 'assets', 'favicon.ico')));


const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
    console.log(`Servidor rodando - http://localhost:${PORT}`);
});
