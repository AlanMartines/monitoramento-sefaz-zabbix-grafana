#!/usr/bin/env python3
#
# ------------------------------------------------------------------------ #
#  - Este programa irá consultar o status do serviço de NFE da receita federal
#  Responsável por realizar a consulta dentro do arquivo statusNFE.txt,
#  nas consultas será pesquisada as linhas do Autorizador e cada linha de serviço
#  deste autorizador, nesse script ele verificará as alterações das “Bolinhas”
#  em cada serviço, se for verde (Disponível) ele apresentará o resultado 1, 2
#  para amarelo (Indisponível) e 0 para Vermelho(Offine).
#
#  - Script criado com base no script do @bernardolankheet.
#
#   Exemplos:
#      $ ./sefaznfe.py <URL> <ESTADO> <STATUS>
#      Neste exemplo o script realiza a consulta do campo de "Autorização" do
#      estado de AM. Retornando o valor 1, 2 ou 0.
# ------------------------------------------------------------------------ #
#
import sys
import random
from bs4 import BeautifulSoup
import cloudscraper

user_agent_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.64',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.172',
]

def request(url):
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': random.choice(user_agent_list),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1'
    }
    response = scraper.get(url, headers=headers)
    return response

def consultar_servico(status):
    if status == "imagens/bola_verde_P.png":
        return 1  # DISPONIVEL
    elif status == "imagens/bola_amarela_P.png":
        return 2  # INDISPONIVEL
    elif status == "imagens/bola_vermelho_P.png":
        return 0  # OFFLINE
    elif status == "-" or status == "":
        return 5  # SEM DADOS
    else:
        return 5  # SEM DADOS

def obter_status(soup, estado, posicao):
    row = soup.find('td', text=estado)
    if row:
        cells = row.find_parent('tr').find_all('td')
        if posicao < len(cells):
            img = cells[posicao].find('img')
            if img:
                return img['src']
            else:
                return cells[posicao].text.strip()
    return None

def main(url, estado, status):
    response = request(url)

    if response.status_code != 200:
        # print("Falha ao obter a página. Status code:", response.status_code)
        print(5)
        sys.exit()

    try:
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as err:
        print("Falha ao processar a página.", err)
        sys.exit()

    status_map = {
        "AUTORIZACAO": 1,
        "RETORNO.AUT": 2,
        "INUTILIZACAO": 3,
        "CONSULTA.PROTOCOLO": 4,
        "SERVICO": 5,
        "TEMPO.MED": 6,
        "CONSULTA.CADASTRO": 7,
        "RECEPCAO.EVENTO": 8
    }

    posicao = status_map.get(status)
    if posicao is None:
        print(5)  # SEM DADOS
        return

    status_img = obter_status(soup, estado, posicao)
    if status_img:
        if status == "TEMPO.MED":
            try:
                tempo_medio = int(status_img)
                if tempo_medio < 200:
                    print(1)  # DISPONIVEL
                elif 200 <= tempo_medio < 1000:
                    print(2)  # INTERMITENTE
                else:
                    print(0)  # CRITICO
            except ValueError:
                print(5)  # SEM DADOS
        else:
            print(consultar_servico(status_img))
    else:
        print(5)  # SEM DADOS

if __name__ == "__main__":
    if len(sys.argv) != 4:
        # Usage: ./sefaznfe.py <URL> <ESTADO> <STATUS>
        print(5)
        sys.exit()
    
    url = sys.argv[1]
    estado = sys.argv[2]
    status = sys.argv[3]
    main(url, estado, status)
