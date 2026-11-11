"""Testes da API — main.py.

Precisam de httpx e fastapi (veja requirements-dev.txt). Cada teste sobe
o app contra um vault temporário, então não dependem do vault real.
"""
import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch, vault, glossario):
    """App apontado para o vault de fixture.

    main.py assume caminhos de container (`/app/lib`, `/app/static`), então
    o teste sobrescreve STATIC_DIR e coloca o lib/ do repo no path. Sem isso
    o import do StaticFiles estoura fora do container.
    """
    monkeypatch.setenv("INDEX_PATH", str(vault))
    monkeypatch.setenv("APP_VERSION", "9.9.9-teste")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "static"))
    if str(RAIZ / "lib") not in sys.path:
        sys.path.insert(0, str(RAIZ / "lib"))
    for mod in ("main", "indexador", "explicador"):
        sys.modules.pop(mod, None)
    import main
    importlib.reload(main)
    # O glossário de fixture fica ao lado do índice, como no vault real.
    main.glossario = main.load_glossario(glossario)
    with TestClient(main.app) as c:
        yield c


class TestVersion:
    def test_devolve_a_versao_do_env(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200
        assert r.json()["version"] == "9.9.9-teste"

    def test_devolve_sanidade_do_indice(self, client):
        """O HEALTHCHECK do Docker depende deste endpoint não varrer o vault."""
        corpo = client.get("/api/version").json()
        assert corpo["commands"] > 0
        assert corpo["files"] > 0
        assert "glossario" in corpo


class TestSearch:
    def test_busca_por_palavra(self, client):
        r = client.get("/api/search", params={"q": "armazenamento"})
        assert r.status_code == 200
        assert r.json()["count"] > 0

    def test_busca_modo_comando(self, client):
        r = client.get("/api/search", params={"q": "ip", "mode": "cmd"})
        assert r.json()["count"] > 0

    def test_busca_vazia_nao_erro(self, client):
        assert client.get("/api/search", params={"q": ""}).status_code == 200


class TestExplicar:
    def test_explica_flag_conhecida(self, client):
        r = client.post("/api/explicar", json={"comando": "docker run -d nginx"})
        assert r.status_code == 200
        partes = r.json()["partes"]
        d = next(p for p in partes if p["flag"] == "-d")
        assert d["documentado"] is True
        assert d["descricao"]

    def test_subcomando_tem_precedencia(self, client):
        """docker compose up -d ≠ docker run -d."""
        r = client.post("/api/explicar", json={"comando": "docker compose up -d"})
        d = next(p for p in r.json()["partes"] if p["flag"] == "-d")
        assert "stack" in d["descricao"]

    def test_flag_desconhecida_nao_inventa(self, client):
        r = client.post("/api/explicar", json={"comando": "docker run --xyz"})
        p = next(x for x in r.json()["partes"] if x["flag"] == "--xyz")
        assert p["documentado"] is False
        assert p["descricao"] == ""

    def test_comando_vazio(self, client):
        corpo = client.post("/api/explicar", json={"comando": "   "}).json()
        assert corpo["erro"] == "comando vazio"

    def test_glossario_reporta_cobertura(self, client):
        r = client.get("/api/glossario")
        assert r.json()["entradas"] > 0
        assert r.json()["comandos"] > 0


class TestReload:
    def test_reload_atualiza_os_dois_indices(self, client, vault):
        r = client.post("/api/reload")
        assert r.status_code == 200
        corpo = r.json()
        assert corpo["count"] > 0
        assert "glossario" in corpo, "reload tem que recarregar o glossário também"
