# Indexador — buscador de comandos do seu Segundo Cérebro

Indexa todos os arquivos `.md` de uma pasta de **Index** (um acervo de
comandos documentados) e permite buscar comandos por palavra-chave ou
pelo texto do próprio comando — no terminal (REPL com autocomplete) ou
via interface web (FastAPI). Sem LLM, sem rede, sem dependência externa:
só Python da biblioteca padrão (+ FastAPI/uvicorn para a web).

Faz parte do ecossistema **Lavinia**, mas é independente: ele **só** lê
a pasta do Index, sem LLM, e ignora tudo fora dela.

## O que é isso

- Você mantém um vault Markdown com seus comandos num formato simples
  (seções `##`, blocos ` ```bash `, comentários `2+ espaços #`).
- O Indexador indexa esse vault em memória e devolve o comando certo em
  milissegundos — tolerante a erro de digitação/acento, com sinônimos.

Use o `Index/modelo.md` (em `examples/`) como ponto de partida para o
formato dos seus arquivos.

## Requisitos

- Python 3.8+ (testado em 3.14) — ou Docker, se preferir as imagens.
- Módulo `readline` da stdlib (nativo em Linux/macOS).
- **Opcional, copiar comando pra área de transferência:** `xclip`/`wl-copy`/`pbcopy`. Sem isso, o REPL imprime o comando.

## Instalação e uso (CLI)

```bash
git clone https://github.com/nerdsouza/indexador.git
cd indexador
python3 busca_index.py
```

Prompt interativo `busca>`:

| Entrada | O que faz |
|---|---|
| `armazenamento` | busca por palavra-chave em comando, comentário, seção, label e nome do arquivo. Por padrão, prioriza arquivos cujo nome bate com o termo (stem match); se nenhum bater, busca por relevância. Prefixo `/` (ex: `/du -sh`) desliga o stem match e busca só no texto do comando |
| `2` | escolhe o resultado `#2` — copia pra área de transferência, ou imprime se não houver clipboard |
| `Tab` | autocompleta a linha contra todos os comandos indexados |

A variável de ambiente `INDEX_PATH` aponta para o seu Index
(default: `~/cerebro-vault/Index`). O glossário `Index/glossario-flags.md`
**não** entra no índice de comandos (ele alimenta o explicador
`/api/explicar`). Pastas e arquivos ocultos (`.obsidian/`, `.stfolder/`)
também são ignorados.

### REPL via Docker (sem instalar nada)

```bash
docker run --rm -it -v ~/cerebro-vault/Index:/vault:ro ghcr.io/nerdsouza/indexador-cli
```

Ou use o wrapper `./buscador-cli`: baixa (ou builda) a imagem e sobe o
REPL com o seu Index montado em `/vault` — tudo automático.

## Uso como cliente (web, sem build)

```bash
curl -sO https://raw.githubusercontent.com/nerdsouza/indexador/main/docker-compose.client.yml
docker compose -f docker-compose.client.yml up -d
# interface em http://127.0.0.1:8000 — API em /api/search?q=...
```

Variáveis: `APP_VERSION` (default `3.2.0`), `PORT` (`8000`), `INDEX_PATH`
(`$HOME/cerebro-vault/Index`). O vault entra read-only em `/vault`.
REPL sob demanda: `docker compose -f docker-compose.client.yml run --rm cli`.

## Imagens Docker

| Imagem | Uso |
|---|---|
| `ghcr.io/nerdsouza/indexador` | Web (FastAPI + uvicorn, porta 8000) |
| `ghcr.io/nerdsouza/indexador-cli` | CLI leve (REPL, ~74 MB) |

Tags: `<versão>` e `latest`. Para desenvolver a partir do código, veja
`docker-compose.yml` (dev, com `build:`) e a seção a seguir.

## Desenvolvimento

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest            # 45 testes
docker compose build && docker compose up -d   # web dev em 127.0.0.1:8000
```

Layout:

- `lib/indexador.py` — motor de indexação e busca (compartilhado CLI/web)
- `lib/explicador.py` — decompõe um comando e explica cada flag (texto vem só do glossário)
- `busca_index.py` — REPL do terminal
- `main.py` + `static/` — API e interface web
- `tests/` — contrato do motor; se quebrar aqui, quebra nos dois clientes

Formato esperado dos arquivos do Index: ver `examples/modelo.md`.

Regras do parser:

- Fora de bloco ` ```bash `, só linhas `## ` são lidas (viram a "seção");
- Dentro do bloco, linha começando com `#` vira **label** (vale do
  label até o fim do bloco);
- Comando e comentário são separados por **2+ espaços seguidos de `#`**;
- Arquivos fora do padrão ainda são lidos (sem comentário/label).

## Limitações conhecidas

- Não interpreta YAML complexo nem tabelas Markdown fora de blocos de código
- Pressupõe UTF-8; `Tab`-completion exige um terminal real com `readline`
- Sem persistência: o índice é recriado em memória a cada execução

*Mantido por NerdSouza. Licença MIT — veja `LICENSE`.*
