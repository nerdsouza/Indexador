"""Testes do motor de indexação e busca — lib/indexador.py.

Cobre o contrato que a CLI e a web dependem. Se quebrar aqui, quebra nos dois.
"""
import pytest

from indexador import (
    build_vocab, load_index, parse_file, search, search_cmd, strip_accents,
)


class TestParse:
    def test_extrai_comando_comentario_secao_label(self, vault):
        entries = parse_file(vault / "exemplo.md", vault)
        ip = next(e for e in entries if e["cmd"] == "ip -br a")
        assert ip["comment"] == "mostra interfaces em uma linha"
        assert ip["section"] == "Rede"
        assert ip["file"] == "exemplo.md"

    def test_label_vale_ate_o_proximo_label(self, vault):
        entries = parse_file(vault / "exemplo.md", vault)
        systemctl = [e for e in entries if e["cmd"].startswith("systemctl")]
        assert systemctl, "os comandos com label deveriam existir"
        assert all(e["label"] == "Verificar servico" for e in systemctl)

    def test_um_espaco_antes_do_hash_nao_e_comentario(self, tmp_path):
        """Regra do parser: 2+ espaços antes do # são obrigatórios."""
        p = tmp_path / "a.md"
        p.write_text("```bash\nls -l # isto e comando, nao comentario\n```\n",
                     encoding="utf-8")
        entry = parse_file(p, tmp_path)[0]
        assert entry["cmd"] == "ls -l # isto e comando, nao comentario"
        assert entry["comment"] == ""

    def test_fora_do_bloco_nao_e_comando(self, vault):
        """Texto corrido fora de fence não entra no índice."""
        entries = parse_file(vault / "exemplo.md", vault)
        assert all(e["cmd"] for e in entries)

    def test_arquivo_inexistente_nao_quebra(self, tmp_path):
        assert parse_file(tmp_path / "nao-existe.md", tmp_path) == []


class TestEnriquecimento:
    def test_label_vira_comentario_quando_falta(self, vault):
        """Camada 1: a causa raiz dos 895 comandos sem descrição."""
        entries = load_index(str(vault))
        systemctl = next(e for e in entries if e["cmd"] == "systemctl status nginx")
        assert systemctl["label"] == "Verificar servico"
        assert systemctl["comment"] == "Verificar servico"

    def test_comentario_existente_nao_e_sobrescrito(self, vault):
        entries = load_index(str(vault))
        df = next(e for e in entries if e["cmd"] == "df -h")
        assert df["comment"] == "uso de disco legível"

    def test_camada2_usa_comando_mais_longo_como_exemplo(self, vault):
        """rsync curto é ambíguo; a versão mais longa desambigua."""
        entries = load_index(str(vault))
        curto = next(e for e in entries
                     if e["cmd"] == "rsync -avzP /a/ /b/" and not e["comment"])
        assert curto["example"], "esperava exemplo derivado de um rsync mais longo"

    def test_campo_example_existe_em_todas_as_entradas(self, vault):
        """A UI lê item.example — se faltar a chave, quebra o render."""
        for entry in load_index(str(vault)):
            assert "example" in entry

    def test_label_e_section_nao_sao_sobrescritos(self, vault):
        """O ranking pesa cada campo; não pode ser contaminado."""
        entries = load_index(str(vault))
        ip = next(e for e in entries if e["cmd"] == "ip -br a")
        assert ip["section"] == "Rede"
        assert ip["comment"] == "mostra interfaces em uma linha"


class TestBusca:
    def test_and_exige_todos_os_termos(self, vault):
        """AND tem prioridade, mas o fallback pra OR é comportamento documentado.

        Com `zpool inexistente` o AND não acha nada, então a busca relaxa
        pra OR e devolve o que casa com um dos termos. É proposital — está
        no README — mas é exatamente o tipo de coisa que um teste precisa
        travar pra não virar surpresa depois.
        """
        entries = load_index(str(vault))
        vocab = build_vocab(entries)
        res_and, _ = search(entries, "zpool status", vocab)
        assert [e["cmd"] for e in res_and] == ["zpool status Storage"], \
            "com os dois termos bate, o AND tem que valer"

        res_or, _ = search(entries, "zpool inexistente", vocab)
        assert res_or, "o fallback pra OR traz o que casa com um dos termos"

    def test_and_encontra_quando_ambos_batem(self, vault):
        entries = load_index(str(vault))
        res, _ = search(entries, "zpool storage", build_vocab(entries))
        assert [e["cmd"] for e in res] == ["zpool status Storage"]

    def test_corrige_erro_de_digitacao(self, vault):
        entries = load_index(str(vault))
        vocab = build_vocab(entries)
        res, notice = search(entries, "armazenmento", vocab)
        assert notice == [("armazenmento", "armazenamento")]
        assert res, "a correção deveria trazer os resultados da seção Armazenamento"

    def test_modo_comando_prioriza_prefixo(self, vault):
        entries = load_index(str(vault))
        res = search_cmd(entries, "ip")
        assert res[0]["cmd"].startswith("ip")
        assert all("ip" in e["cmd"] for e in res)

    def test_busca_vazia_nao_quebra(self, vault):
        entries = load_index(str(vault))
        assert search(entries, "", build_vocab(entries)) == ([], [])
        assert search_cmd(entries, "  ") == []


class TestUtilitarios:
    @pytest.mark.parametrize("entrada,saida", [
        ("armazenamento", "armazenamento"),
        ("ação", "acao"),
        ("pá", "pa"),
    ])
    def test_strip_accents(self, entrada, saida):
        assert strip_accents(entrada) == saida

    def test_vocab_so_ignora_palavras_curtas(self, vault):
        """Palavra de <4 letras polui o vocabulário e piora o fuzzy."""
        vocab = build_vocab(load_index(str(vault)))
        assert all(len(w) >= 4 for w in vocab)
