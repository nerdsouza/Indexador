"""Fixtures compartilhadas.

Os testes rodam contra um vault temporário, nunca contra
~/cerebro-vault/Index real — assim o resultado não depende de quantos
comandos você já escreveu e o teste não quebra quando o vault muda.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "lib"))


VAULT_FIXTURE = """---
titulo: Fixture
---
## Rede
```bash
ip -br a                 # mostra interfaces em uma linha
ip route                 # tabela de rotas
ss -tulpn                # portas em escuta
```

## Armazenamento
```bash
df -h                    # uso de disco legível
zpool status Storage     # estado do pool ZFS
```

## Com label
```bash
# Verificar servico
systemctl status nginx
systemctl restart nginx
```

## Comando ambiguo
```bash
rsync -avzP /a/ /b/
rsync -avzP /a/ /b/ --delete   # remove do destino o que nao existe na origem
```

## Sem comentario
```bash
pct start 300
qm set 101 --memory 2048
```
"""

GLOSSARIO_FIXTURE = """---
titulo: Glossario fixture
---
## docker
```bash
docker ps -a              # -a   # mostra tambem os parados
docker run -d            # -d   # detached: segundo plano
docker compose up -d     # -d   # sobe a stack em background
docker run --name nome   # --name # define o nome
docker run -p 8080:80    # -p   # publica porta
```

## systemctl
```bash
systemctl status nome    #       # estado da unit
systemctl restart nome   #       # reinicia
```
"""


@pytest.fixture
def vault(tmp_path):
    """Vault mínimo, com todos os formatos que o parser precisa cobrir."""
    index = tmp_path / "Index"
    index.mkdir()
    (index / "exemplo.md").write_text(VAULT_FIXTURE, encoding="utf-8")
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html><body>fixture</body></html>",
                                        encoding="utf-8")
    return index


@pytest.fixture
def glossario(tmp_path):
    """Glossário com flag ambígua de propósito (docker -d x2)."""
    path = tmp_path / "glossario-flags.md"
    path.write_text(GLOSSARIO_FIXTURE, encoding="utf-8")
    return path
