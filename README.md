# Monitoramento Sefaz Zabbix/Grafana
Monitoramento para [Consultar Disponibilidade](https://hom.nfe.fazenda.gov.br/portal/disponibilidade.aspx) dos serviços da Sefaz via Zabbix e Grafana.

![image](https://github.com/user-attachments/assets/85db4740-54b4-46a0-8680-875c1f585515)

Dados recentes do Zabbix:

![image](https://github.com/user-attachments/assets/aaaf7e64-374b-4aef-8926-58349d91e7ea)

![image](https://github.com/user-attachments/assets/ee3bce29-42f7-4225-827f-2702d66a98c7)

![image](https://github.com/user-attachments/assets/7b702c2b-184c-4f1b-8958-3dbc193206f4)

# Requisitos
```
python 3
bs4
requests
cloudscraper
cfscrape
```

# Uso
```
./sefaznfe.py <URL> <ESTADO> <STATUS>
./sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx AM SERVICO
```

# Debian / Ubuntu
```sh
apt install python3 python3-pip
pip3 install bs4
pip3 install requests
pip3 install cloudscraper
pip3 install cfscrape
```

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
- 1: 🟢DISPONIVEL
- 2: 🟡INDISPONIVEL
- 0: 🔴OFFLINE
- 5: ⚪SEM DADOS

### O resultado sem erro para TEMPO.MED
- 1: 🟢DISPONIVEL
- 2: 🟡INTERMITENTE
- 0: 🔴CRITICO
- 5: ⚪SEM DADOS

# Como Usar
Para usar os templates deste repositório, siga estas etapas:

1. Importe os templates do Zabbix.
2. Importe o dashboard do Grafana.
3. Monitore o sistema SEFAZ e visualize os dados no Grafana.

# Testado com
- Zabbix: v7.0
- Grafana: v11

# [Downgrade para Zabbix v5.4:](https://github.com/AlanMartines/monitoramento-sefaz-zabbix-grafana/issues/2#issue-2629057062)
**No arquivo YAML altere a versão de 7.0 para 5.4 e mude a tag do grupo, depois de criar os grupos manualmente, realize a importação** Obs: Lembre-se de não marcar a opção de CRIAR NOVO GRUPO no zabbix, apenas editar o atual existente.
 
### Atual:
```yaml
zabbix_export:
  version: '7.0'
  host_groups:
```

### Alteração:
```yaml
zabbix_export:
  version: '5.4'
  groups:
```

### Antes de importar os arquivos YAML, crie os grupos manualmente.
Grupo de Hosts: Monitoramento Sefaz Grupo de Templates: Templates/Sefaz

# Contribuições

[Contribuições](CONTRIBUTING.md) são bem-vindas! Por favor, abra uma issue ou pull request.

# Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

[GIT original](https://github.com/everaldoscabral/Monitoramento_Sefaz)
