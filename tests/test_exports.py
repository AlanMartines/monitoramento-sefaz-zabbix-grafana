"""Verificações estáticas dos exports do Zabbix e dos dashboards do Grafana."""

import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sefaznfe as m  # noqa: E402

ZABBIX_EXPORTS = sorted(ROOT.glob("zbx_export_*.yaml")) + sorted(ROOT.glob("withcertificate/zbx_export_*.yaml"))
DASHBOARDS = sorted(ROOT.glob("*.json")) + sorted(ROOT.glob("withcertificate/*.json"))


@pytest.mark.parametrize("path", ZABBIX_EXPORTS, ids=lambda p: p.name)
def test_export_zabbix_valido(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["zabbix_export"]["version"] == "7.0"


@pytest.mark.parametrize("path", DASHBOARDS, ids=lambda p: p.name)
def test_dashboard_json_valido(path):
    assert "panels" in json.loads(path.read_text(encoding="utf-8"))


def template_portal():
    data = yaml.safe_load((ROOT / "zbx_export_template_portal.yaml").read_text(encoding="utf-8"))
    return data["zabbix_export"]["templates"][0]


def test_template_portal_cobre_todos_os_servicos_do_script():
    rule = template_portal()["discovery_rules"][0]
    keys = {p["key"] for p in rule["item_prototypes"]}
    servicos = {re.search(r",(.+)\]$", k).group(1) for k in keys if k.startswith("sefaz.nfe.status[")}
    assert servicos == set(m.STATUS_MAP)


def test_template_portal_jsonpath_usa_chaves_do_script():
    rule = template_portal()["discovery_rules"][0]
    for proto in rule["item_prototypes"]:
        path = proto["preprocessing"][0]["parameters"][0]
        chave = re.search(r"\['([^']+)'\]$", path).group(1)
        assert chave in set(m.STATUS_MAP) | {"TEMPO.MED.MS"}, path


def test_timeout_dos_itens_maior_que_deadline_do_script():
    for path in ZABBIX_EXPORTS:
        for match in re.finditer(r"timeout: (\d+)s", path.read_text(encoding="utf-8")):
            assert int(match.group(1)) > m.DEADLINE, path.name
