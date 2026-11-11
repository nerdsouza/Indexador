from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from pathlib import Path
import os, sys
sys.path.insert(0, "/app/lib")
from indexador import load_index, build_vocab, search, search_cmd
from explicador import load_glossario, explicar
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title="Busca-Index Web")
INDEX_PATH = os.getenv("INDEX_PATH", "/vault")
STATIC_DIR = os.getenv("STATIC_DIR", "/app/static")


def _ler_versao():
    """Versão em três níveis: env do build > arquivo VERSION > fallback.

    O env ganha porque é o que o Dockerfile injeta. O arquivo cobre o
    `python main.py` local, onde não há build. O fallback é só pra nunca
    devolver string vazia num /api/version.
    """
    env = os.getenv("APP_VERSION")
    if env and env != "dev":
        return env
    try:
        versao = Path("/app/VERSION").read_text(encoding="utf-8").strip()
        if versao:
            return versao
    except Exception:
        pass
    return env or "dev"


VERSAO = _ler_versao()

entries = load_index(INDEX_PATH)
vocab = build_vocab(entries)
glossario = load_glossario()

class Busca(BaseModel):
    q: str = ""
    mode: str = ""

class Explicar(BaseModel):
    comando: str = ""

@app.get("/api/search")
def api_search(q: str = "", mode: str = ""):
    if mode == "cmd":
        res = search_cmd(entries, q)
        return {"results": res, "notice": [], "count": len(res)}
    res, notice = search(entries, q, vocab)
    return {"results": res, "notice": notice, "count": len(res)}

@app.post("/api/explicar")
def api_explicar(payload: Explicar):
    """Decompõe um comando e explica cada flag. O texto vem só do glossário."""
    if not payload.comando.strip():
        return {"base": "", "partes": [], "sem_fonte": [], "erro": "comando vazio"}
    return explicar(payload.comando, glossario)

@app.get("/api/glossario")
def api_glossario():
    """Tamaho da cobertura atual do glossário de flags."""
    return {"entradas": len(glossario),
            "comandos": len({k[0].split()[0] for k in glossario})}

@app.get("/api/version")
def api_version():
    """Versão e sanidade do serviço. Não varre o vault — só lê o que já
    está em memória, que é o que torna o HEALTHCHECK do Docker barato."""
    return {
        "version": VERSAO,
        "commands": len(entries),
        "files": len({e["file"] for e in entries}),
        "glossario": len(glossario),
    }

@app.post("/api/reload")
def api_reload():
    global entries, vocab, glossario
    entries = load_index(INDEX_PATH); vocab = build_vocab(entries)
    glossario = load_glossario()
    return {"count": len(entries), "files": len({e["file"] for e in entries}),
            "glossario": len(glossario)}

@app.get("/")
def root():
    return Response((Path(STATIC_DIR) / "index.html").read_text(encoding="utf-8"),
                    media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "no-store"})

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
