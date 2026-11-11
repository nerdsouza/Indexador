FROM python:3.14-alpine

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn

# A versão vem do arquivo VERSION no build — fonte única de verdade.
# `docker build --build-arg APP_VERSION=$(cat VERSION) .`
# O compose já faz isso; o fallback mantém o build manual funcionando.
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

COPY lib/ ./lib/
COPY main.py VERSION ./
COPY static/ ./static/

ENV PORT=8000

# O app só lê o vault e serve arquivos; não precisa de privilégios de root.
RUN addgroup -S app && adduser -S -G app app
USER app

EXPOSE 8000

# Sonda leve: /api/version responde mesmo com o índice grande, porque não
# varre o vault — só devolve o que já está em memória.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/version', timeout=4).status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
