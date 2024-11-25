FROM public.ecr.aws/lambda/python:3.9

# Instale dependências necessárias
RUN yum install -y wget tar xz

# Baixe e instale o FFmpeg
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xJf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-static/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-*-static ffmpeg-release-amd64-static.tar.xz


# Copie o código da função
COPY transcribe_streaming.py ${LAMBDA_TASK_ROOT}

# Copie o arquivo requirements.txt
COPY requirements_docker.txt .

# Instale todas as dependências do requirements.txt
RUN pip install -r requirements_docker.txt --target "${LAMBDA_TASK_ROOT}"

# Defina o comando de entrada para a função Lambda
CMD ["transcribe_streaming.lambda_handler"]
