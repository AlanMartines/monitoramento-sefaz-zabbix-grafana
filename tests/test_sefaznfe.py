"""Testes do sefaznfe.py usando a tabela real do portal salva em fixtures/.

Não acessam a rede: a leitura da página é substituída pelo HTML do fixture,
modificado em cada cenário.
"""

import json
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sefaznfe as m  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "disponibilidade.html"
URL = "https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx"
AUTORIZADORES = ["AM", "BA", "GO", "MG", "MS", "MT", "PE", "PR", "RS", "SP",
                 "SVAN", "SVRS", "SVC-AN", "SVC-RS"]


@pytest.fixture
def html():
    return FIXTURE.read_text(encoding="utf-8")


def checker_for(page_html):
    checker = m.NFEStatusChecker()
    checker._fetch_page = lambda url: BeautifulSoup(page_html, "html.parser")
    return checker


def status(page_html, autorizador, servico):
    return checker_for(page_html).get_service_status(URL, autorizador, servico)


def edit(page_html, changes):
    """Aplica {(autorizador, coluna): ('img', src) | ('text', valor)} na tabela."""
    soup = BeautifulSoup(page_html, "html.parser")
    rows = {r.td.get_text(strip=True): r
            for r in soup.find(id=m.TABLE_ID).find_all("tr")[1:]}
    for (autorizador, coluna), (kind, value) in changes.items():
        cell = rows[autorizador].find_all("td")[coluna]
        if kind == "img":
            cell.img["src"] = value
        else:
            cell.clear()
            cell.string = value
    return str(soup)


def test_fixture_tem_todos_os_autorizadores(html):
    assert sorted(checker_for(html).get_all_status(URL)) == sorted(AUTORIZADORES)


@pytest.mark.parametrize("autorizador,servico,esperado", [
    ("AM", "AUTORIZACAO", 1),
    ("SVC-RS", "INUTILIZACAO", 5),        # célula vazia no portal
    ("SVC-RS", "CONSULTA.CADASTRO", 5),
    ("RS", "TEMPO.MED", 5),               # portal mostra '-'
    ("svc-an", "servico", 1),             # aceita minúsculas
])
def test_pagina_real(html, autorizador, servico, esperado):
    assert status(html, autorizador, servico) == esperado


@pytest.mark.parametrize("src,esperado", [
    ("imagens/bola_verde_P.png", 1),
    ("imagens/bola_amarela_P.png", 2),
    ("imagens/bola_vermelho_P.png", 0),
    ("imagens/outra.png", 5),
])
def test_cores(html, src, esperado):
    page = edit(html, {("BA", 1): ("img", src)})
    assert status(page, "BA", "AUTORIZACAO") == esperado


@pytest.mark.parametrize("texto,esperado,ms", [
    ("150", 1, 150),
    ("450 ms", 2, 450),
    ("1.250", 0, 1250),
    ("-", 5, None),
])
def test_tempo_medio(html, texto, esperado, ms):
    page = edit(html, {("GO", 6): ("text", texto)})
    assert status(page, "GO", "TEMPO.MED") == esperado
    assert checker_for(page).get_all_status(URL)["GO"].get("TEMPO.MED.MS") == ms


def test_autorizador_parecido_nao_casa(html):
    # "AN" não pode casar com SVAN nem SVC-AN
    assert status(html, "AN", "SERVICO") == m.STATUS_CODES["ERRO_COLETA"]


def test_servico_invalido(html):
    assert status(html, "AM", "FOO") == m.STATUS_CODES["ERRO_COLETA"]


def test_coluna_nova_no_portal(html):
    """Uma coluna inserida no meio da tabela não pode deslocar os serviços."""
    page = edit(html, {("BA", 1): ("img", "imagens/bola_vermelho_P.png"),
                       ("GO", 6): ("text", "1500")})
    soup = BeautifulSoup(page, "html.parser")
    for i, row in enumerate(soup.find(id=m.TABLE_ID).find_all("tr")):
        cell = soup.new_tag("th" if i == 0 else "td")
        cell.string = "Nova Coluna" if i == 0 else "x"
        row.find_all(["th", "td"])[2].insert_after(cell)
    page = str(soup)
    assert status(page, "BA", "AUTORIZACAO") == 0
    assert status(page, "GO", "TEMPO.MED") == 0
    assert status(page, "AM", "RECEPCAO.EVENTO") == 1


def test_layout_quebrado(html):
    page = html.replace(m.TABLE_ID, "outra").replace(m.TABLE_CLASS, "outra")
    assert status(page, "AM", "AUTORIZACAO") == m.STATUS_CODES["ERRO_COLETA"]
    with pytest.raises(m.CollectError):
        checker_for(page).get_all_status(URL)


def test_json_bate_com_modo_individual(html):
    page = edit(html, {("AM", 1): ("img", "imagens/bola_amarela_P.png"),
                       ("BA", 5): ("img", "imagens/bola_vermelho_P.png"),
                       ("GO", 6): ("text", "300")})
    dados = checker_for(page).get_all_status(URL)
    for autorizador, servicos in dados.items():
        for servico in m.STATUS_MAP:
            assert servicos[servico] == status(page, autorizador, servico), (autorizador, servico)


@pytest.mark.parametrize("url,valida", [
    (URL, True),
    ("http://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx", True),
    ("https://fazenda.gov.br/", True),
    ("https://www.nfe.fazenda.gov.br.exemplo.com/", False),
    ("https://exemplofazenda.gov.br/", False),
    ("ftp://www.nfe.fazenda.gov.br/", False),
])
def test_validacao_de_url(url, valida):
    assert m.NFEStatusChecker()._validate_url(url) is valida


def test_main_json_erro_sem_log_no_stdout(monkeypatch, capsys):
    """Em falha, o modo JSON imprime só o JSON de erro (o Zabbix lê stdout+stderr)."""
    monkeypatch.setattr(sys, "argv", ["sefaznfe.py", "https://exemplo.com/", "JSON"])
    m.main()
    out, err = capsys.readouterr()
    assert err == ""
    assert "erro" in json.loads(out)


def test_main_modo_individual_imprime_so_o_numero(monkeypatch, capsys, html):
    monkeypatch.setattr(m.NFEStatusChecker, "_fetch_page",
                        lambda self, url: BeautifulSoup(html, "html.parser"))
    monkeypatch.setattr(sys, "argv", ["sefaznfe.py", URL, "AM", "SERVICO"])
    m.main()
    out, err = capsys.readouterr()
    assert (out, err) == ("1\n", "")


@pytest.mark.parametrize("mudancas,esperado", [
    ({}, 1),
    ({("BA", 3): ("img", "imagens/bola_amarela_P.png")}, 2),
    ({("BA", 3): ("img", "imagens/bola_amarela_P.png"), ("BA", 8): ("img", "imagens/bola_vermelho_P.png")}, 0),
    ({("BA", 6): ("text", "5000")}, 1),   # tempo médio não entra no status geral
])
def test_status_geral(html, mudancas, esperado):
    assert checker_for(edit(html, mudancas)).get_all_status(URL)["BA"]["GERAL"] == esperado


def test_status_geral_sem_dados():
    assert m._pior_status([5, 5, 3]) == 5
