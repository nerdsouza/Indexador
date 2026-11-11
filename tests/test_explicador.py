"""Testes do explicador de comando — lib/explicador.py.

O explicador tem duas regras que não podem quebrar em silêncio:
  1. Nunca inventar texto. Flag sem fonte é "não documentado", não palpite.
  2. A chave é (comando, subcomando, flag) — nunca flag solta, porque
     74 das 360 flags do índice têm significados diferentes por comando.
"""
import pytest

from explicador import explicar, load_glossario, split_command


class TestSplit:
    def test_expande_flag_curta_agrupada(self):
        base, flags, args, _ = split_command("rsync -avzP /a/ /b/")
        assert base == "rsync"
        assert flags == ["-a", "-v", "-z", "-P"]
        assert args == ["/a/", "/b/"]

    def test_flag_longa_com_igual(self):
        """Com `--name=web` o valor fica dentro do token da flag."""
        base, flags, args, _ = split_command("docker run --name=web -d nginx")
        assert base == "docker"
        assert "--name" in flags
        assert args == ["run", "nginx"], "o valor não vira argumento separado"

    def test_flag_longa_com_espaco(self):
        _, flags, args, _ = split_command("docker run --name web -d nginx")
        assert "--name" in flags
        assert "web" in args, "o valor da flag deve ir para os argumentos"

    def test_flag_curta_com_valor(self):
        _, flags, args, _ = split_command("docker run -p 8080:80 nginx")
        assert "-p" in flags
        assert "8080:80" in args

    def test_double_dash_separa(self):
        _, flags, args, _ = split_command("tar -cf a.tar -- -weird-file")
        assert "-weird-file" in args, "depois de -- tudo é argumento"

    def test_ignora_sudo(self):
        base, flags, _, _ = split_command("sudo docker ps -a")
        assert base == "docker"
        assert "-a" in flags

    def test_comando_vazio(self):
        base, flags, args, _ = split_command("   ")
        assert base == ""
        assert flags == [] and args == []


class TestGlossario:
    def test_le_formato_de_tres_partes(self, glossario):
        gl = load_glossario(glossario)
        assert gl[("docker", "-a")] == "mostra tambem os parados"

    def test_flag_ambigua_por_subcomando(self, glossario):
        """O caso que define o desenho: -d significa duas coisas em docker."""
        gl = load_glossario(glossario)
        assert gl[("docker run", "-d")] == "detached: segundo plano"
        assert gl[("docker compose", "-d")] == "sobe a stack em background"

    def test_arquivo_inexistente_devolve_vazio(self, tmp_path):
        assert load_glossario(tmp_path / "nao-existe.md") == {}


class TestExplicar:
    def test_separa_flag_do_argumento(self, glossario):
        r = explicar("docker run -d nginx", load_glossario(glossario))
        flags = [p["flag"] for p in r["partes"] if p["tipo"] == "flag"]
        args = [p["flag"] for p in r["partes"] if p["tipo"] == "arg"]
        assert flags == ["-d"]
        assert args == ["run", "nginx"]

    def test_subcomando_tem_precedencia_sobre_a_base(self, glossario):
        """docker compose up -d NÃO pode devolver a descricao de docker run -d."""
        r = explicar("docker compose up -d", load_glossario(glossario))
        d = next(p for p in r["partes"] if p["flag"] == "-d")
        assert d["descricao"] == "sobe a stack em background"

    def test_flag_sem_fonte_nao_inventa_texto(self, glossario):
        """Contrato central: ausência de fonte é dita, não preenchida."""
        r = explicar("docker run --invalida xyz", load_glossario(glossario))
        p = next(x for x in r["partes"] if x["flag"] == "--invalida")
        assert p["documentado"] is False
        assert p["descricao"] == "", "não pode haver texto inventado"
        assert "--invalida" in r["sem_fonte"]

    def test_comando_vazio_nao_quebra(self, glossario):
        r = explicar("", load_glossario(glossario))
        assert r["base"] == ""
        assert r["erro"] == "comando vazio"

    def test_comando_sem_flag_ainda_lista_argumentos(self, glossario):
        r = explicar("docker ps -a", load_glossario(glossario))
        assert r["base"] == "docker"
        assert any(p["tipo"] == "arg" for p in r["partes"])
