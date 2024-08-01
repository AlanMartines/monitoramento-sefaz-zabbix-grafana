# Zabbix/Grafana Monitoramento Sefaz
Monitoramento do status dos serviços da Sefaz via Zabbix.

![image](https://github.com/user-attachments/assets/85db4740-54b4-46a0-8680-875c1f585515)

Dados recentes do Zabbix:

![image](https://github.com/user-attachments/assets/aaaf7e64-374b-4aef-8926-58349d91e7ea)

![image](https://github.com/user-attachments/assets/ee3bce29-42f7-4225-827f-2702d66a98c7)

![image](https://github.com/user-attachments/assets/7b702c2b-184c-4f1b-8958-3dbc193206f4)

# Requisitos
```
python 3
beautifulsoup4
cloudscraper
requests
openssl
```

# Uso
```
./sefaznfe.py <URL> <ESTADO> <STATUS>
./sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx AM SERVICO
```

# Debian / Ubuntu
<pre>apt install python3 python3-pip
pip3 install bs4
pip3 install requests
pip3 install cloudscraper</pre>

Caso já tenha o pip instalado e queira instalar as dependencias rode:
```
pip3 install requirements.txt
```

Copie o arquivo sefaznfe.py para /usr/lib/zabbix/externalscripts, altere suas permissões para o usuários zabbix. 
<pre>
chown zabbix. /usr/lib/zabbix/externalscripts/sefaznfe.py
chmod a+x /usr/lib/zabbix/externalscripts/sefaznfe.py
</pre>

# sefaznfe.py
### O resultado sem erro para AUTORIZACAO, RETORNO.AUT INUTILIZACAO CONSULTA.PROTOCOLO SERVICO CONSULTA.CADASTRO RECEPCAO.EVENTO
- 1: DISPONIVEL
- 2: INDISPONIVEL
- 0: OFFLINE
- 5: SEM DADOS

### O resultado sem erro para TEMPO.MED
- 1: DISPONIVEL
- 2: INTERMITENTE
- 0: CRITICO
- 5: SEM DADOS

[GIT original](https://github.com/everaldoscabral/Monitoramento_Sefaz)
