import json
import os
import asyncio
import subprocess
import boto3
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from amazon_transcribe.utils import apply_realtime_delay
from pydub import AudioSegment
import aiofile
from botocore.exceptions import NoCredentialsError

# Configurações
S3_BUCKET = os.environ["S3_BUCKET"]
REGION = "us-east-1"
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 1
CHUNK_SIZE = 1024 * 8

# Função de manipulação dos eventos de transcrição
class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.transcription = ""

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if not result.is_partial:  # Armazena apenas transcrições completas
                for alt in result.alternatives:
                    self.transcription += alt.transcript + " "  # Acumula a transcrição final completa

# Função principal de transcrição
async def basic_transcribe(file_path):
    client = TranscribeStreamingClient(region=REGION)
    stream = await client.start_stream_transcription(
        language_code="pt-BR",
        media_sample_rate_hz=SAMPLE_RATE,
        media_encoding="pcm",
    )

    async def write_chunks():
        async with aiofile.AIOFile(file_path, "rb") as afp:
            reader = aiofile.Reader(afp, chunk_size=CHUNK_SIZE)
            await apply_realtime_delay(stream, reader, BYTES_PER_SAMPLE, SAMPLE_RATE, CHANNEL_NUMS)
        await stream.input_stream.end_stream()

    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(write_chunks(), handler.handle_events())
    return handler.transcription.strip()

# Função handler do Lambda
def lambda_handler(event, context):
    print(event)
    # ffmpeg_version = subprocess.run(["/usr/local/bin/ffmpeg", "-version"], capture_output=True, text=True)
    # print("FFmpeg Version:", ffmpeg_version.stdout)
    # Extrai o nome do arquivo do evento
    try:
        body = json.loads(event['body'])
        file_name = body["media_object_key"]

        print("Body recebido:", body)
        print("Chave 'media_object_key':", body.get("media_object_key"))

    except KeyError:
        return {
            "statusCode": 400, "body": "fileName is required in the request body.",
            "headers": {"Content-Type": "application/json"}
            }

    s3 = boto3.client("s3", region_name=REGION)

    # Cria um diretório temporário para armazenar os arquivos
    os.makedirs('/tmp/audios/', exist_ok=True)
    local_file_path = f"/tmp/{file_name}"

    # Baixa o arquivo do S3
    try:
        s3.download_file(S3_BUCKET, file_name, local_file_path)

    except NoCredentialsError:
        return {
            "statusCode": 403, "body": "Credentials not available.",
            "headers": {"Content-Type": "application/json"}
            }
    
    except Exception as e:
        return {
            "statusCode": 500, "body": f"Error downloading file: {str(e)}",
            "headers": {"Content-Type": "application/json"}
            }

    print("Tamanho do arquivo do audio: ", os.path.getsize(local_file_path))
    # Converte o áudio para WAV com a configuração correta
    try:
        audio = AudioSegment.from_file(local_file_path, format="webm")
        print("objeto audio: ", audio)
        converted_file_name = file_name.split("/")[-1]
        converted_file_path = f"/tmp/converted_{converted_file_name[:-5]}.wav"
        audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)
        audio.export(converted_file_path, format="wav")
    except Exception as e:
        return {
            "statusCode": 500, "body": f"Error processing audio file: {str(e)}",
            "headers": {"Content-Type": "application/json"}
            }

    # Transcreve o áudio
    try:
        transcription = asyncio.run(basic_transcribe(converted_file_path))
    except Exception as e:
        return {
            "statusCode": 500, "body": f"Error during transcription: {str(e)}",
            "headers": {"Content-Type": "application/json"}
            }

    # Limpa os arquivos temporários
    os.remove(local_file_path)
    os.remove(converted_file_path)

    # Retorna o resultado da transcrição
    print(transcription)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "job_transcript": transcription
        }),
        "headers": {"Content-Type": "application/json"}
    }
