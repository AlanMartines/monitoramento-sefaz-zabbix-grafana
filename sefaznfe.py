#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para consultar o status do serviço de NFE da Receita Federal.

Verifica o status dos serviços do portal da NFE e retorna:
- 1: Disponível (verde)
- 2: Indisponível (amarelo) 
- 0: Offline (vermelho)
- 5: Sem dados

Uso:
    python sefaznfe.py <URL> <ESTADO> <STATUS>

Exemplo:
    python sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx AM AUTORIZACAO
"""

import sys
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuração de logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Constantes
TIMEOUT = 10
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.3
RETRY_STATUS_CODES = [500, 502, 503, 504, 429]

# Status codes de retorno
STATUS_CODES = {
    'DISPONIVEL': 1,
    'INDISPONIVEL': 2, 
    'OFFLINE': 0,
    'SEM_DADOS': 5
}

# Headers mais realistas
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

# Mapeamento de status para posições na tabela
STATUS_MAP = {
    "AUTORIZACAO": 1,
    "RETORNO.AUT": 2,
    "INUTILIZACAO": 3,
    "CONSULTA.PROTOCOLO": 4,
    "SERVICO": 5,
    "TEMPO.MED": 6,
    "CONSULTA.CADASTRO": 7,
    "RECEPCAO.EVENTO": 8
}


class NFEStatusChecker:
    """Classe para verificar status dos serviços NFE."""
    
    def __init__(self):
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria uma sessão HTTP com retry e configurações otimizadas."""
        session = requests.Session()
        
        # Configuração de retry
        retry_strategy = Retry(
            total=MAX_RETRIES,
            status_forcelist=RETRY_STATUS_CODES,
            backoff_factor=BACKOFF_FACTOR,
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(HEADERS)
        
        return session
    
    def _validate_url(self, url: str) -> bool:
        """Valida se a URL é válida e do domínio correto."""
        try:
            parsed = urlparse(url)
            return (parsed.scheme in ['http', 'https'] and 
                   'fazenda.gov.br' in parsed.netloc.lower())
        except Exception:
            return False
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Faz a requisição HTTP e retorna o BeautifulSoup da página."""
        if not self._validate_url(url):
            logger.error("URL inválida ou não é do domínio fazenda.gov.br")
            return None
        
        try:
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            
            # Verifica se o conteúdo é HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                logger.error("Resposta não é HTML")
                return None
            
            # Parse do HTML com error handling
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Verifica se a página foi carregada corretamente
            if not soup.find('table') and not soup.find('td'):
                logger.error("Estrutura HTML esperada não encontrada")
                return None
                
            return soup
            
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição")
        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
        
        return None
    
    def _interpret_status_image(self, status_src: str) -> int:
        """Interpreta o status baseado na imagem/texto."""
        if not status_src:
            return STATUS_CODES['SEM_DADOS']
        
        status_src = status_src.lower().strip()
        
        # Verifica imagens de status
        if 'bola_verde' in status_src or 'green' in status_src:
            return STATUS_CODES['DISPONIVEL']
        elif 'bola_amarela' in status_src or 'yellow' in status_src:
            return STATUS_CODES['INDISPONIVEL']
        elif 'bola_vermelho' in status_src or 'red' in status_src:
            return STATUS_CODES['OFFLINE']
        
        # Verifica texto direto
        if status_src in ['disponível', 'online', 'ativo']:
            return STATUS_CODES['DISPONIVEL']
        elif status_src in ['indisponível', 'instável']:
            return STATUS_CODES['INDISPONIVEL']
        elif status_src in ['offline', 'inativo']:
            return STATUS_CODES['OFFLINE']
        elif status_src in ['-', '', 'n/a']:
            return STATUS_CODES['SEM_DADOS']
        
        return STATUS_CODES['SEM_DADOS']
    
    def _handle_tempo_medio(self, tempo_text: str) -> int:
        """Processa tempo médio e retorna status baseado na performance."""
        try:
            # Remove caracteres não numéricos e converte
            tempo_clean = ''.join(filter(str.isdigit, tempo_text))
            if not tempo_clean:
                return STATUS_CODES['SEM_DADOS']
            
            tempo_medio = int(tempo_clean)
            
            if tempo_medio < 200:
                return STATUS_CODES['DISPONIVEL']
            elif 200 <= tempo_medio < 1000:
                return STATUS_CODES['INDISPONIVEL']
            else:
                return STATUS_CODES['OFFLINE']
                
        except (ValueError, TypeError):
            return STATUS_CODES['SEM_DADOS']
    
    def _find_estado_row(self, soup: BeautifulSoup, estado: str) -> Optional[Any]:
        """Encontra a linha da tabela correspondente ao estado."""
        # Busca mais flexível por estado
        estado_variations = [
            estado.upper(),
            estado.lower(), 
            estado.capitalize(),
            estado
        ]
        
        for variation in estado_variations:
            # Busca exata
            row = soup.find('td', string=variation)
            if row:
                return row
            
            # Busca parcial (caso tenha espaços ou formatação)
            row = soup.find('td', string=lambda text: text and variation in text.strip())
            if row:
                return row
        
        return None
    
    def get_service_status(self, url: str, estado: str, status_type: str) -> int:
        """
        Obtém o status do serviço para o estado especificado.
        
        Args:
            url: URL do portal de disponibilidade
            estado: Sigla do estado (ex: 'AM', 'SP')
            status_type: Tipo de status a consultar (ex: 'AUTORIZACAO')
            
        Returns:
            int: Código de status (0, 1, 2, ou 5)
        """
        # Validação de parâmetros
        if not all([url, estado, status_type]):
            return STATUS_CODES['SEM_DADOS']
        
        # Busca a página
        soup = self._fetch_page(url)
        if not soup:
            return STATUS_CODES['SEM_DADOS']
        
        # Validação do tipo de status
        posicao = STATUS_MAP.get(status_type.upper())
        if posicao is None:
            logger.error(f"Tipo de status inválido: {status_type}")
            return STATUS_CODES['SEM_DADOS']
        
        # Encontra a linha do estado
        estado_cell = self._find_estado_row(soup, estado.upper())
        if not estado_cell:
            logger.error(f"Estado não encontrado: {estado}")
            return STATUS_CODES['SEM_DADOS']
        
        # Obtém todas as células da linha
        try:
            row = estado_cell.find_parent('tr')
            cells = row.find_all('td')
            
            if posicao >= len(cells):
                logger.error(f"Posição {posicao} não existe na tabela")
                return STATUS_CODES['SEM_DADOS']
            
            target_cell = cells[posicao]
            
            # Processa tempo médio de forma especial
            if status_type.upper() == "TEMPO.MED":
                cell_text = target_cell.get_text(strip=True)
                return self._handle_tempo_medio(cell_text)
            
            # Procura por imagem primeiro
            img = target_cell.find('img')
            if img and img.get('src'):
                return self._interpret_status_image(img['src'])
            
            # Se não há imagem, usa o texto
            cell_text = target_cell.get_text(strip=True)
            return self._interpret_status_image(cell_text)
            
        except (AttributeError, IndexError) as e:
            logger.error(f"Erro ao processar tabela: {e}")
            return STATUS_CODES['SEM_DADOS']


def main():
    """Função principal do script."""
    if len(sys.argv) != 4:
        print(STATUS_CODES['SEM_DADOS'])
        sys.exit(1)
    
    url = sys.argv[1]
    estado = sys.argv[2]
    status_type = sys.argv[3]
    
    checker = NFEStatusChecker()
    result = checker.get_service_status(url, estado, status_type)
    print(result)


if __name__ == "__main__":
    main()
