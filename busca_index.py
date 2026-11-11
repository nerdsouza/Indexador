#!/usr/bin/env python3
"""
Lavinia — Busca rápida de comandos no Index do segundo cérebro.
REPL local, sem LLM: usa a biblioteca compartilhada lib/indexador.py
(a mesma do backend web), com busca por palavra-chave (tolerante a erro
de digitação/acento e sinônimos), autocomplete via Tab e cópia do comando
escolhido para a área de transferência.
"""
import readline
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "lib"))

from indexador import (  # noqa: E402
    INDEX, load_index, build_vocab, search,
)


def copy_to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        # fallback para xclip ou pbcopy (fora de um desktop, nenhum existe)
        if shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            return True
        if shutil.which("pbcopy"):
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        return False


PAGE_SIZE = 20


def _print_box(results, start, count):
    print(f"\nMostrando {start + 1}-{start + count} de {len(results)} resultados:\n")
    for i, e in enumerate(results[start:start + count], start=start + 1):
        label = f"#{i}" + (f" · {e['label']}" if e["label"] else "")
        print(label)
        print(e["cmd"])
        if e.get("comment"):
            print(f"# {e['comment']}")
        if e.get("example") and not e.get("comment"):
            print(f"ex.: `{e['example']}`")
        print(e.get("section", ""))
        print("-" * 40)


def _print_notice(notice):
    if not notice:
        return
    for old, new in notice:
        print(f"Aproximando `{old}` para `{new}`")


def print_results(results, notice=None, limit=PAGE_SIZE):
    _print_notice(notice)
    if not results:
        print("(nada encontrado)")
        return 0
    total = len(results)
    shown = 0
    while shown < total:
        _print_box(results, shown, min(limit, total - shown))
        shown += limit
        if shown < total:
            if input("\nPressione Enter para ver mais... (ou q para sair) ").strip().lower() == "q":
                break
    return shown


def show_more(limit=PAGE_SIZE):
    global _last_results, _last_notice, _shown
    if not _last_results:
        print("Nenhuma busca anterior.")
        return
    shown = _shown
    total = len(_last_results)
    while shown < total:
        _print_box(_last_results, shown, min(limit, total - shown))
        shown += limit
        if shown < total:
            if input("\nPressione Enter para ver mais... (ou q para sair) ").strip().lower() == "q":
                break
    _shown = shown


def setup_autocomplete(entries):
    def complete(text, state):
        if state == 0:
            matches = [e["cmd"] for e in entries if e["cmd"].lower().startswith(text.lower())]
            return matches[state] if state < len(matches) else None
        return None
    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")


def try_select(query):
    entries = load_index()
    vocab = build_vocab(entries)
    results, notice = search(entries, query, vocab)
    if not results:
        print("(nenhum resultado)")
        return None
    if len(results) == 1:
        return results[0]["cmd"]
    print_results(results, notice)
    try:
        idx = input("\nEscolha o número do comando: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    try:
        i = int(idx) - 1
        if 0 <= i < len(results):
            return results[i]["cmd"]
    except ValueError:
        pass
    return None


def main():
    entries = load_index()
    vocab = build_vocab(entries)
    setup_autocomplete(entries)
    global _last_results, _last_notice, _shown
    _last_results = []
    _last_notice = None
    _shown = 0
    print(f"Indexador CLI — {len(entries)} comandos de {INDEX}")
    while True:
        try:
            query = input("busca> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        cmd = try_select(query)
        if cmd is None:
            continue
        if copy_to_clipboard(cmd):
            print(f"✓ Copiado: {cmd}")
        else:
            # Sem clipboard (ex.: container headless): imprime p/ copiar na mão.
            print(f"Sem área de transferência disponível. Comando:\n{cmd}")


if __name__ == "__main__":
    main()
