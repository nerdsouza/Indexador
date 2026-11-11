"""
lib/explicador.py — decompõe um comando e explica cada flag a partir do
glossário no vault.

Regra de ouro: o texto exibido SEMPRE vem do glossário
(`Index/glossario-flags.md`). Flag que não está documentada aparece como
"não documentado" — nunca com texto inventado.

A chave de lookup é `(comando_base, flag)`, nunca a flag sozinha: no índice,
74 das 360 flags têm significados diferentes dependendo do comando.
"""

import os
import re
from pathlib import Path

GLOSSARIO = Path(os.getenv("INDEX_PATH", str(Path.home() / "cerebro-vault" / "Index"))) / "glossario-flags.md"
FENCE = "```"
# `comando  # flag  # descrição` — o flag e a descrição são separados por
# qualquer sequência de 2+ espaços seguida de #, o mesmo separador de
# comment do indexador.py.
GLOSS_LINE = re.compile(r'^(?P<cmd>\S.*?)\s{2,}#\s*(?P<flag>\S+)\s+#\s*(?P<desc>.+?)\s*$')


def strip_accents(value):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", value)
                   if unicodedata.category(c) != "Mn")


def load_glossario(path=GLOSSARIO):
    """Lê o glossário e devolve {(chave, flag): descrição}.

    A chave inclui o subcomando quando existe: `docker run -d` e
    `docker compose down -d` são flags diferentes com o mesmo nome, e
    `docker -d` nem existe. Guarda as duas formas (só a base, e base+subcomando)
    para que uma entrada de subcomando não seja lost quando o usuário cola o
    comando completo, nem precise repetir a flag na seção do subcomando.
    """
    if not Path(path).exists():
        return {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    out, in_code = {}, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(FENCE):
            in_code = not in_code
            continue
        if not in_code or not stripped or stripped.startswith("#"):
            continue
        match = GLOSS_LINE.match(line)
        if not match:
            continue
        partes = match.group("cmd").split()
        base = partes[0]
        sub = partes[1] if len(partes) > 1 and not partes[1].startswith("-") else ""
        desc = match.group("desc").strip()
        flag = match.group("flag")
        out[(base, flag)] = desc
        if sub:
            out[(f"{base} {sub}", flag)] = desc
    return out


def split_command(cmdline):
    """Separa a linha em (base, flags[], argumentos[], tokens).

    Suporta flag curta agrupada (`-avzP` -> -a -v -z -P), flag longa
    (`--restart`), e flag com valor (`-p 8080:80`, `--name x`).
    Não tenta ser um parser de shell completo — só o necessário pro glossário.
    """
    tokens = cmdline.strip().split()
    if not tokens:
        return "", [], [], []
    # ignora sudo/env na frente
    while tokens and tokens[0] in ("sudo", "doas", "env", "nohup"):
        tokens.pop(0)
    if not tokens:
        return "", [], [], []
    base = tokens.pop(0)
    flags, args = [], []
    take_next = False
    for token in tokens:
        if take_next:
            args.append(token)
            take_next = False
            continue
        if token == "--":
            args.extend(tokens)
            break
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            flags.append(name)
            if "=" not in token:
                take_next = True   # --name valor
        elif token.startswith("-") and len(token) > 1:
            # agrupada? -avzP -> -a -v -z -P ; senão -p 8080
            corpo = token[1:]
            if all(c.isalpha() for c in corpo):
                for ch in corpo:
                    flags.append("-" + ch)
            else:
                flags.append(token)
                take_next = True
        else:
            args.append(token)
    return base, flags, args, tokens


def explicar(cmdline, glossario=None):
    """Devolve a decomposição do comando com a descrição de cada flag."""
    glossario = glossario if glossario is not None else load_glossario()
    base, flags, args, tokens = split_command(cmdline)
    if not base:
        return {"base": "", "partes": [], "sem_fonte": [], "erro": "comando vazio"}
    # Tenta a chave mais específica (base + subcomando) antes da genérica:
    # `docker run -d` é a flag do `run`, não a do `docker` solto.
    sub = ""
    for token in tokens:
        if not token.startswith("-"):
            sub = token
            break
    chave = f"{base} {sub}" if sub else base
    partes, sem_fonte = [], []
    for flag in flags:
        desc = glossario.get((chave, flag)) or glossario.get((base, flag))
        if desc:
            partes.append({"tipo": "flag", "flag": flag, "descricao": desc,
                           "documentado": True})
        else:
            partes.append({"tipo": "flag", "flag": flag, "descricao": "",
                           "documentado": False})
            sem_fonte.append(flag)
    for arg in args:
        partes.append({"tipo": "arg", "flag": arg, "descricao": "",
                       "documentado": False})
    return {
        "base": base,
        "comando": cmdline.strip(),
        "partes": partes,
        "sem_fonte": sem_fonte,
        "erro": None,
    }
