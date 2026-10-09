#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para consultar o status do serviço de NFE da Receita Federal.

Verifica o status dos serviços do portal da NFE e retorna:
- 1: Disponível (verde)
- 2: Indisponível (amarelo)
- 0: Offline (vermelho)
- 3: Erro na coleta (portal inacessível, timeout ou layout da página mudou)
- 5: Sem dados (o portal não informa status para o serviço)

Uso:
    python sefaznfe.py <URL> <AUTORIZADOR> <STATUS>

Diagnóstico (mostra o motivo de um código 3):
    SEFAZ_NFE_DEBUG=1 python sefaznfe.py <URL> <AUTORIZADOR> <STATUS>

Exemplo:
    python sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx AM AUTORIZACAO
"""

import os
import sys
import time
import logging
import unicodedata
from typing import Optional, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# O Zabbix junta stdout e stderr no valor de um external check: qualquer log
# misturado ao número deixa o item "não suportado". Por isso o log só é emitido
# quando SEFAZ_NFE_DEBUG=1 (uso manual, para diagnóstico).
logger = logging.getLogger(__name__)
if os.environ.get('SEFAZ_NFE_DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
else:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False

# Tempo total máximo de execução, em segundos. Deve ser menor que o timeout
# do item no Zabbix (30s no template), senão o Zabbix encerra o script antes
# de ele responder e o item fica "não suportado". O portal costuma levar de
# 4 a 10s para responder.
DEADLINE = 25
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15
MAX_ATTEMPTS = 2
RETRY_DELAY = 0.5

ALLOWED_DOMAIN = 'fazenda.gov.br'
TABLE_ID = 'ctl00_ContentPlaceHolder1_gdvDisponibilidade2'
TABLE_CLASS = 'tabelaListagemDados'

# Status codes de retorno
STATUS_CODES = {
    'DISPONIVEL': 1,
    'INDISPONIVEL': 2,
    'OFFLINE': 0,
    'ERRO_COLETA': 3,
    'SEM_DADOS': 5
}

# Sem 'br' no Accept-Encoding: o requests só descompacta brotli se o pacote
# brotli estiver instalado; sem ele a página chegaria ilegível.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
}

# Cabeçalho da coluna no portal (normalizado) e posição usada como fallback
STATUS_MAP = {
    "AUTORIZACAO": ("AUTORIZACAO", 1),
    "RETORNO.AUT": ("RETORNO AUTORIZACAO", 2),
    "INUTILIZACAO": ("INUTILIZACAO", 3),
    "CONSULTA.PROTOCOLO": ("CONSULTA PROTOCOLO", 4),
    "SERVICO": ("STATUS SERVICO", 5),
    "TEMPO.MED": ("TEMPO MEDIO", 6),
    "CONSULTA.CADASTRO": ("CONSULTA CADASTRO", 7),
    "RECEPCAO.EVENTO": ("RECEPCAO EVENTO", 8)
}


class CollectError(Exception):
    """Falha ao obter ou interpretar a página (vira o código ERRO_COLETA)."""


def _normalize(text: str) -> str:
    """Remove acentos, dígitos de versão e espaços extras; retorna em maiúsculas."""
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c) and not c.isdigit())
    return ' '.join(text.upper().split())


class NFEStatusChecker:
    """Classe para verificar status dos serviços NFE."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _validate_url(self, url: str) -> bool:
        """Valida se a URL é http(s) e pertence ao domínio fazenda.gov.br."""
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        host = (parsed.hostname or '').lower()
        return (parsed.scheme in ('http', 'https') and
                (host == ALLOWED_DOMAIN or host.endswith('.' + ALLOWED_DOMAIN)))

    def _fetch_page(self, url: str) -> BeautifulSoup:
        """Faz a requisição HTTP respeitando o DEADLINE e retorna o HTML."""
        if not self._validate_url(url):
            raise CollectError(f"URL inválida ou fora do domínio {ALLOWED_DOMAIN}: {url}")

        start = time.monotonic()
        last_error = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = DEADLINE - (time.monotonic() - start)
            if remaining <= 1:
                break
            try:
                # A sessão guarda o cookie de detecção do ASP.NET; sem ele o
                # portal responde com redirecionamento em loop.
                response = self.session.get(
                    url, timeout=(min(CONNECT_TIMEOUT, remaining), min(READ_TIMEOUT, remaining)))
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()
                if 'html' not in content_type:
                    raise CollectError(f"Resposta não é HTML ({content_type})")
                return BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"Tentativa {attempt} falhou: {e}")
                time.sleep(min(RETRY_DELAY, max(0, DEADLINE - (time.monotonic() - start))))

        raise CollectError(f"Falha ao acessar o portal: {last_error or 'tempo esgotado'}")

    def _find_table(self, soup: BeautifulSoup):
        """Localiza a tabela de disponibilidade."""
        table = soup.find('table', id=TABLE_ID) or soup.find('table', class_=TABLE_CLASS)
        if not table:
            raise CollectError("Tabela de disponibilidade não encontrada (layout do portal mudou?)")
        return table

    def _column_index(self, table, status_type: str) -> int:
        """Descobre a coluna do serviço pelo cabeçalho; usa a posição fixa como fallback."""
        header_text, fallback = STATUS_MAP[status_type]
        header_row = table.find('tr')
        headers = [_normalize(c.get_text()) for c in header_row.find_all(['th', 'td'])]
        if header_text in headers:
            return headers.index(header_text)
        logger.warning(f"Cabeçalho '{header_text}' não encontrado; usando posição {fallback}")
        return fallback

    def _find_row_cells(self, table, autorizador: str) -> Optional[List]:
        """Retorna as células da linha cujo autorizador é exatamente o informado."""
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if cells and cells[0].get_text(strip=True).upper() == autorizador:
                return cells
        return None

    def _interpret_status_image(self, status_src: str) -> int:
        """Interpreta o status baseado na imagem/texto."""
        status_src = (status_src or '').lower().strip()

        if 'bola_verde' in status_src:
            return STATUS_CODES['DISPONIVEL']
        if 'bola_amarela' in status_src:
            return STATUS_CODES['INDISPONIVEL']
        if 'bola_vermelh' in status_src:
            return STATUS_CODES['OFFLINE']

        if status_src in ('disponível', 'online', 'ativo'):
            return STATUS_CODES['DISPONIVEL']
        if status_src in ('indisponível', 'instável'):
            return STATUS_CODES['INDISPONIVEL']
        if status_src in ('offline', 'inativo'):
            return STATUS_CODES['OFFLINE']

        return STATUS_CODES['SEM_DADOS']

    def _handle_tempo_medio(self, tempo_text: str) -> int:
        """Processa tempo médio e retorna status baseado na performance."""
        tempo_clean = ''.join(filter(str.isdigit, tempo_text))
        if not tempo_clean:
            return STATUS_CODES['SEM_DADOS']

        tempo_medio = int(tempo_clean)
        if tempo_medio < 200:
            return STATUS_CODES['DISPONIVEL']
        if tempo_medio < 1000:
            return STATUS_CODES['INDISPONIVEL']
        return STATUS_CODES['OFFLINE']

    def get_service_status(self, url: str, autorizador: str, status_type: str) -> int:
        """
        Obtém o status do serviço para o autorizador especificado.

        Args:
            url: URL do portal de disponibilidade
            autorizador: Autorizador como aparece no portal (ex: 'AM', 'SVRS', 'SVC-AN')
            status_type: Tipo de status a consultar (ex: 'AUTORIZACAO')

        Returns:
            int: Código de status (0, 1, 2, 3 ou 5)
        """
        autorizador = autorizador.strip().upper()
        status_type = status_type.strip().upper()

        if status_type not in STATUS_MAP:
            logger.error(f"Tipo de status inválido: {status_type}")
            return STATUS_CODES['ERRO_COLETA']

        try:
            table = self._find_table(self._fetch_page(url))
            posicao = self._column_index(table, status_type)

            cells = self._find_row_cells(table, autorizador)
            if cells is None:
                raise CollectError(f"Autorizador não encontrado no portal: {autorizador}")
            if posicao >= len(cells):
                raise CollectError(f"Coluna {posicao} não existe na linha de {autorizador}")
        except CollectError as e:
            logger.error(str(e))
            return STATUS_CODES['ERRO_COLETA']

        target_cell = cells[posicao]

        if status_type == "TEMPO.MED":
            return self._handle_tempo_medio(target_cell.get_text(strip=True))

        img = target_cell.find('img')
        if img and img.get('src'):
            return self._interpret_status_image(img['src'])
        return self._interpret_status_image(target_cell.get_text(strip=True))


def main():
    """Função principal do script."""
    if len(sys.argv) != 4:
        logger.error(__doc__.strip())
        print(STATUS_CODES['ERRO_COLETA'])
        sys.exit(1)

    url, autorizador, status_type = sys.argv[1:4]

    checker = NFEStatusChecker()
    result = checker.get_service_status(url, autorizador, status_type)
    print(result)


if __name__ == "__main__":
    main()
