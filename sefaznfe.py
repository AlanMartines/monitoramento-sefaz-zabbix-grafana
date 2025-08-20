#!/usr/bin/env python3
"""
Monitor de Status dos Serviços NFe - Sefaz
============================================

Este programa consulta o status dos serviços de NFe da Receita Federal,
verificando a disponibilidade dos autorizadores por estado e serviço.

Códigos de retorno:
- 1: DISPONÍVEL (verde)
- 2: INDISPONÍVEL/INTERMITENTE (amarelo)  
- 0: OFFLINE/CRÍTICO (vermelho)
- 5: SEM DADOS/ERRO

Uso:
    python sefaznfe.py <URL> <ESTADO> <SERVICO>
    
Exemplo:
    python sefaznfe.py "https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx" "AM" "AUTORIZACAO"
"""

import sys
import time
import random
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException, Timeout, ConnectionError
from urllib3.util.retry import Retry


# Configuração de logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Classe para representar o status de um serviço"""
    code: int
    description: str
    
    @classmethod
    def from_image_src(cls, src: str) -> 'ServiceStatus':
        """Cria ServiceStatus baseado no src da imagem"""
        status_mapping = {
            "imagens/bola_verde_P.png": cls(1, "DISPONÍVEL"),
            "imagens/bola_amarela_P.png": cls(2, "INDISPONÍVEL"), 
            "imagens/bola_vermelho_P.png": cls(0, "OFFLINE"),
        }
        return status_mapping.get(src, cls(5, "SEM DADOS"))


class SefazNFeMonitor:
    """Monitor principal dos serviços NFe"""
    
    # User agents mais recentes e variados
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
    ]
    
    # Mapeamento de serviços para posições na tabela
    SERVICE_POSITIONS = {
        "AUTORIZACAO": 1,
        "RETORNO.AUT": 2, 
        "INUTILIZACAO": 3,
        "CONSULTA.PROTOCOLO": 4,
        "SERVICO": 5,
        "TEMPO.MED": 6,
        "CONSULTA.CADASTRO": 7,
        "RECEPCAO.EVENTO": 8,
    }
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Inicializa o monitor
        
        Args:
            timeout: Timeout para requisições HTTP
            max_retries: Número máximo de tentativas
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria uma sessão HTTP configurada com retry e timeout"""
        session = requests.Session()
        
        # Configuração de retry
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,  # Espera progressiva entre tentativas
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Gera headers realistas para a requisição"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    def _validate_url(self, url: str) -> bool:
        """Valida se a URL é do domínio esperado"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.endswith('fazenda.gov.br')
        except Exception:
            return False
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        Faz requisição HTTP com tratamento de erros
        
        Args:
            url: URL para fazer a requisição
            
        Returns:
            Response object ou None em caso de erro
        """
        if not self._validate_url(url):
            logger.error(f"URL não autorizada: {url}")
            return None
        
        headers = self._get_headers()
        
        try:
            # Delay aleatório para parecer mais humano
            time.sleep(random.uniform(0.5, 2.0))
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
                verify=True  # Verificar certificados SSL
            )
            
            # Verifica se a resposta foi bem-sucedida
            if response.status_code == 200:
                # Verifica se não é uma página de erro ou bloqueio
                content_lower = response.text.lower()
                error_indicators = [
                    'quarentena', 'bloqueado', 'access denied', 
                    'forbidden', 'erro', 'indisponível'
                ]
                
                if any(indicator in content_lower for indicator in error_indicators):
                    logger.warning("Página indica bloqueio ou erro")
                    return None
                
                logger.info(f"Requisição bem-sucedida para {url}")
                return response
            else:
                logger.warning(f"Status code não OK: {response.status_code}")
                return None
                
        except Timeout:
            logger.error(f"Timeout ao acessar {url}")
        except ConnectionError:
            logger.error(f"Erro de conexão ao acessar {url}")
        except RequestException as e:
            logger.error(f"Erro na requisição: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
        
        return None
    
    def _parse_html(self, html_content: str) -> Optional[BeautifulSoup]:
        """
        Faz parsing do HTML com tratamento de erros
        
        Args:
            html_content: Conteúdo HTML
            
        Returns:
            Objeto BeautifulSoup ou None em caso de erro
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Verifica se encontrou estrutura esperada
            tables = soup.find_all('table')
            if not tables:
                logger.warning("Nenhuma tabela encontrada no HTML")
                return None
                
            return soup
            
        except Exception as e:
            logger.error(f"Erro ao fazer parsing do HTML: {e}")
            return None
    
    def _get_service_status(self, soup: BeautifulSoup, estado: str, posicao: int) -> Optional[str]:
        """
        Extrai o status do serviço da tabela HTML
        
        Args:
            soup: Objeto BeautifulSoup
            estado: Estado a pesquisar
            posicao: Posição da coluna do serviço
            
        Returns:
            Src da imagem ou texto do status
        """
        try:
            # Procura pela célula com o texto do estado
            estado_cell = soup.find('td', string=estado)
            
            if not estado_cell:
                # Tenta busca case-insensitive
                estado_cell = soup.find('td', string=lambda text: text and text.strip().upper() == estado.upper())
            
            if not estado_cell:
                logger.warning(f"Estado {estado} não encontrado")
                return None
            
            # Encontra a linha pai
            row = estado_cell.find_parent('tr')
            if not row:
                logger.warning("Linha pai não encontrada")
                return None
            
            # Encontra todas as células da linha
            cells = row.find_all('td')
            
            if posicao >= len(cells):
                logger.warning(f"Posição {posicao} não existe (total: {len(cells)})")
                return None
            
            target_cell = cells[posicao]
            
            # Procura por imagem primeiro
            img = target_cell.find('img')
            if img and 'src' in img.attrs:
                return img['src']
            
            # Se não encontrou imagem, retorna o texto
            text = target_cell.get_text(strip=True)
            return text if text else None
            
        except Exception as e:
            logger.error(f"Erro ao extrair status: {e}")
            return None
    
    def _process_tempo_medio(self, tempo_str: str) -> ServiceStatus:
        """
        Processa o tempo médio e retorna status correspondente
        
        Args:
            tempo_str: String com o tempo médio
            
        Returns:
            ServiceStatus correspondente
        """
        try:
            tempo_str = tempo_str.strip().replace('NI', '').replace('-', '')
            
            if not tempo_str or tempo_str.lower() in ['ni', 'não informado', '']:
                return ServiceStatus(5, "SEM DADOS")
            
            tempo_medio = int(float(tempo_str))
            
            if tempo_medio < 200:
                return ServiceStatus(1, "DISPONÍVEL")
            elif 200 <= tempo_medio < 1000:
                return ServiceStatus(2, "INTERMITENTE") 
            else:
                return ServiceStatus(0, "CRÍTICO")
                
        except (ValueError, TypeError):
            logger.warning(f"Erro ao processar tempo médio: {tempo_str}")
            return ServiceStatus(5, "SEM DADOS")
    
    def check_service_status(self, url: str, estado: str, servico: str) -> ServiceStatus:
        """
        Verifica o status de um serviço específico
        
        Args:
            url: URL da página de disponibilidade
            estado: Estado a verificar (ex: 'AM', 'SP')
            servico: Serviço a verificar (ex: 'AUTORIZACAO')
            
        Returns:
            ServiceStatus com o resultado
        """
        # Valida parâmetros
        if not all([url, estado, servico]):
            logger.error("Parâmetros obrigatórios não fornecidos")
            return ServiceStatus(5, "PARÂMETROS INVÁLIDOS")
        
        estado = estado.strip().upper()
        servico = servico.strip().upper()
        
        if servico not in self.SERVICE_POSITIONS:
            logger.error(f"Serviço {servico} não reconhecido")
            return ServiceStatus(5, "SERVIÇO INVÁLIDO")
        
        # Faz requisição
        response = self._make_request(url)
        if not response:
            return ServiceStatus(5, "ERRO NA REQUISIÇÃO")
        
        # Faz parsing do HTML
        soup = self._parse_html(response.text)
        if not soup:
            return ServiceStatus(5, "ERRO NO PARSING")
        
        # Extrai status do serviço
        posicao = self.SERVICE_POSITIONS[servico]
        status_info = self._get_service_status(soup, estado, posicao)
        
        if not status_info:
            return ServiceStatus(5, "STATUS NÃO ENCONTRADO")
        
        # Processa resultado baseado no tipo de serviço
        if servico == "TEMPO.MED":
            return self._process_tempo_medio(status_info)
        else:
            return ServiceStatus.from_image_src(status_info)


def main():
    """Função principal"""
    if len(sys.argv) != 4:
        print(5)
        logger.error("Número incorreto de argumentos")
        sys.exit(1)
    
    url = sys.argv[1]
    estado = sys.argv[2] 
    servico = sys.argv[3]
    
    try:
        monitor = SefazNFeMonitor()
        result = monitor.check_service_status(url, estado, servico)
        print(result.code)
        
    except KeyboardInterrupt:
        logger.info("Operação cancelada pelo usuário")
        print(5)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        print(5)
        sys.exit(1)


if __name__ == "__main__":
    main()
