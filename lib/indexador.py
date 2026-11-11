#!/usr/bin/env python3
"""Biblioteca de indexação e busca do Busca-Index."""
import difflib
import os
import re
import unicodedata
from pathlib import Path

INDEX = Path(os.getenv("INDEX_PATH", str(Path.home() / "cerebro-vault" / "Index")))
CODE_FENCE = "```"
CMD_RE = re.compile(r'^(?P<cmd>\S.*?)(?:\s{2,}#\s*(?P<comment>.*))?$')
SINONIMOS = {
    "armazenamento": {"disco", "storage", "espaco"}, "disco": {"armazenamento", "storage"},
    "rede": {"network", "net"}, "processo": {"processos", "process"},
    "processos": {"processo", "process"}, "pacote": {"pacotes", "package", "pkg"},
    "pacotes": {"pacote", "package", "pkg"}, "log": {"logs"}, "logs": {"log"},
    "container": {"containers", "docker"}, "permissao": {"permissoes", "chmod", "chown"},
    "permissoes": {"permissao", "chmod", "chown"}, "backup": {"vzdump", "restore", "snapshot"},
}


def strip_accents(value):
    return "".join(c for c in unicodedata.normalize("NFD", value)
                    if unicodedata.category(c) != "Mn")


def starts_with_slash(q: str) -> bool:
    """Return True if the query (after stripping leading whitespace) starts with '/'."""
    return q.lstrip().startswith('/')


def _stem_words(stem: str):
    """Split the file stem into words using non-alnum as separator."""
    import re
    return [w for w in re.split(r'\W+', stem) if w]


def _file_name_score(stem: str, term: str) -> int:
    """
    Score how well the term matches the file stem.
    3: exact stem == term
    2: stem starts with term followed by '-' or '_' (or end)
    1: term appears as a whole word inside stem
    0: no match
    """
    stem_l = stem.lower()
    term_l = term.lower()
    if stem_l == term_l:
        return 3
    # prefix followed by delimiter
    if re.search(rf'^{re.escape(term_l)}[-_]', stem_l):
        return 2
    # whole word inside
    if term_l in _stem_words(stem_l):
        return 1
    return 0


def parse_file(path, index_path=INDEX):
    entries, section, label, in_code = [], "", "", False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return entries
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(CODE_FENCE):
            in_code = not in_code
            label = "" if not in_code else label
            continue
        if not in_code:
            if stripped.startswith("## "):
                section = stripped[3:].strip()
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            label = stripped.lstrip("#").strip()
            continue
        match = CMD_RE.match(line)
        if not match:
            continue
        base = Path(index_path)
        rel = path.relative_to(base) if path.is_relative_to(base) else path.name
        entries.append({
            "cmd": match.group("cmd").strip(),
            "comment": (match.group("comment") or "").strip(),
            "section": section,
            "label": label,
            "example": "",   # preenchido em _enrich_entries (precisa do contexto do arquivo)
            "file": str(rel),
        })
    return entries


# Arquivos que não são comandos: o glossário alimenta o explicador,
# não o índice de comandos.
EXCLUDE_FILES = {"glossario-flags.md"}


def _is_hidden(path: Path, base: Path) -> bool:
    """True se qualquer parte do caminho relativo começa com '.' (.obsidian, .stfolder...)."""
    try:
        rel = path.relative_to(base)
    except ValueError:
        rel = path
    return any(part.startswith(".") for part in rel.parts)


def load_index(index_path=INDEX):
    entries = []
    base = Path(index_path)
    for path in sorted(base.rglob("*.md")):
        if _is_hidden(path, base):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        entries.extend(parse_file(path, index_path))
    return _enrich_entries(entries)


def _enrich_entries(entries):
    """Deriva descrição e exemplo de uso quando o comando não tem comentário.

    Duas camadas, nesta ordem:
      1. Sem comentário inline mas com label de bloco → o label vira descrição.
      2. Ainda sem descrição → procura, entre todos os comandos indexados, um
        mais longo que comece com este. A diferença entre os dois é o que
        desambigua o genérico (`pct set --mp` → `pct set --mp1 tn-data:vol-...`).

    Não altera `label` nem `section`: o ranking pondera cada campo com peso
    próprio e a web usa o label no cabeçalho do grupo.
    """
    todas = [strip_accents(e["cmd"].lower()) for e in entries]
    for entry, chave in zip(entries, todas):
        if not entry["comment"] and entry["label"]:
            entry["comment"] = entry["label"]
        if entry["comment"]:
            continue
        for outra, original in zip(todas, entries):
            if outra.startswith(chave) and outra != chave:
                entry["example"] = original["cmd"]
                break
    return entries


def build_vocab(entries):
    vocab = set()
    for entry in entries:
        text = " ".join([entry["cmd"], entry["comment"], entry["section"], entry["label"]])
        for word in re.split(r"[^a-zA-Z0-9çáéíóúãõâêîôûàü_-]+", text.lower()):
            if len(word) >= 4:
                vocab.add(strip_accents(word))
    return vocab


def _variants(term):
    return {term} | SINONIMOS.get(term, set())


def word_matches(haystack, word):
    return any(variant in haystack for variant in _variants(word))


def _field_score(value, term):
    """Pontua uma ocorrência: início, tamanho e sequência têm prioridade."""
    value = strip_accents(value.lower())
    best = 0.0
    for variant in _variants(term):
        position = value.find(variant)
        if position < 0:
            continue
        # Prefixos e ocorrências próximas ao início são mais relevantes.
        best = max(best, 100.0 - min(position, 80))
        if position == 0:
            best += 35
        if value.startswith(variant + " "):
            best += 15
        best += min(value.count(variant) - 1, 3) * 4
        best += difflib.SequenceMatcher(None, variant, value).ratio() * 10
    return best


def relevance_score(entry, terms):
    """Retorna (termos_encontrados, relevância) sem perder a semântica AND."""
    fields = {
        "cmd": entry["cmd"],
        "comment": entry["comment"],
        "label": entry["label"],
        "section": entry["section"],
        "file": entry["file"],
    }
    weights = {"cmd": 4.0, "comment": 2.0, "label": 2.0, "section": 1.0, "file": 0.25}
    found = 0
    total = 0.0
    for term in terms:
        term_total = max(_field_score(value, term) * weights[key]
                         for key, value in fields.items())
        if term_total > 0:
            found += 1
            total += term_total
    return found, total


def score(entry, terms):
    """Compatibilidade com a API antiga: retorna apenas a relevância."""
    return relevance_score(entry, terms)[1]


def fuzzy_correct(terms, vocab):
    corrected, changed = [], []
    for term in terms:
        if term in vocab:
            corrected.append(term)
            continue
        close = difflib.get_close_matches(term, vocab, n=1, cutoff=0.72)
        if close:
            corrected.append(close[0])
            changed.append((term, close[0]))
        else:
            corrected.append(term)
    return corrected, changed


def _rank(entries, terms, command_mode=False):
    ranked = []
    for position, entry in enumerate(entries):
        found, relevance = relevance_score(entry, terms)
        ranked.append((position, found, relevance, entry))
    if command_mode:
        ranked.sort(key=lambda item: (item[3]["cmd"].lower().find(terms[0]), -item[2], item[0]))
    else:
        ranked.sort(key=lambda item: (-item[1], -item[2], item[0]))
    return [item[3] for item in ranked]


def search(entries, query, vocab):
    raw_terms = [strip_accents(term.lower()) for term in query.split() if term.strip()]
    if not raw_terms:
        return [], []
    # If query starts with '/', skip stem match and use traditional search
    if starts_with_slash(query):
        scored = [(relevance_score(entry, raw_terms), position, entry)
                  for position, entry in enumerate(entries)]
        matched = [item for item in scored if item[0][0] == len(raw_terms)]
        if not matched:
            matched = [item for item in scored if item[0][0] > 0]
        notice = []
        if not matched:
            corrected, changed = fuzzy_correct(raw_terms, vocab)
            if changed:
                scored = [(relevance_score(entry, corrected), position, entry)
                          for position, entry in enumerate(entries)]
                matched = [item for item in scored if item[0][0] == len(corrected)]
                if not matched:
                    matched = [item for item in scored if item[0][0] > 0]
                notice = changed
        matched.sort(key=lambda item: (-item[0][0], -item[0][1], item[1]))
        return [item[2] for item in matched], notice
    # --- Stem-based filtering (when no leading slash) ---
    # Compute file name score for each entry
    file_scores = []
    for entry in entries:
        stem = Path(entry["file"]).stem
        # max score across all terms
        max_term_score = max((_file_name_score(stem, t) for t in raw_terms), default=0)
        file_scores.append(max_term_score)
    max_file_score = max(file_scores) if file_scores else 0
    if max_file_score > 0:
        # Keep only entries with the highest file name score
        filtered = [entry for entry, score in zip(entries, file_scores) if score == max_file_score]
        # Return in original index order, no notice
        return filtered, []
    # Fallback to traditional relevance scoring
    scored = [(relevance_score(entry, raw_terms), position, entry)
              for position, entry in enumerate(entries)]
    matched = [item for item in scored if item[0][0] == len(raw_terms)]
    if not matched:
        matched = [item for item in scored if item[0][0] > 0]
    notice = []
    if not matched:
        corrected, changed = fuzzy_correct(raw_terms, vocab)
        if changed:
            scored = [(relevance_score(entry, corrected), position, entry)
                      for position, entry in enumerate(entries)]
            matched = [item for item in scored if item[0][0] == len(corrected)]
            if not matched:
                matched = [item for item in scored if item[0][0] > 0]
            notice = changed
    matched.sort(key=lambda item: (-item[0][0], -item[0][1], item[1]))
    return [item[2] for item in matched], notice


def _command_proximity(entry, term):
    command = strip_accents(entry["cmd"].lower())
    position = command.find(term)
    if position < 0:
        position = len(command)
    ratio = difflib.SequenceMatcher(None, term, command).ratio()
    return (position, -ratio, len(command))


def search_cmd(entries, term):
    term = strip_accents(term.lower().strip())
    if not term:
        return []
    starts, contains = [], []
    for entry in entries:
        command = strip_accents(entry["cmd"].lower())
        if command.startswith(term):
            starts.append(entry)
        elif term in command:
            contains.append(entry)
    starts.sort(key=lambda entry: _command_proximity(entry, term))
    contains.sort(key=lambda entry: _command_proximity(entry, term))
    return starts + contains
