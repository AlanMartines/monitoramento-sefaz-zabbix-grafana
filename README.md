# Monitoramento Sefaz Zabbix/Grafana
Monitoramento para [Consultar Disponibilidade](https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx) dos serviços da Sefaz via Zabbix e Grafana.

![image](https://github.com/user-attachments/assets/85db4740-54b4-46a0-8680-875c1f585515)

Dados recentes do Zabbix:

![image](https://github.com/user-attachments/assets/aaaf7e64-374b-4aef-8926-58349d91e7ea)

![image](https://github.com/user-attachments/assets/ee3bce29-42f7-4225-827f-2702d66a98c7)

![image](https://github.com/user-attachments/assets/7b702c2b-184c-4f1b-8958-3dbc193206f4)

# Requisitos
```
python 3
beautifulsoup4
requests
```

# Uso
```
./sefaznfe.py <URL> <AUTORIZADOR> <STATUS>
./sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx AM SERVICO
```

`<AUTORIZADOR>` é o nome que aparece na primeira coluna do portal: AM, BA, GO, MG, MS, MT, PE, PR, RS, SP, SVAN, SVRS, SVC-AN ou SVC-RS.

`<STATUS>`: AUTORIZACAO, RETORNO.AUT, INUTILIZACAO, CONSULTA.PROTOCOLO, SERVICO, TEMPO.MED, CONSULTA.CADASTRO ou RECEPCAO.EVENTO.

Para ver o motivo de um retorno 3 (erro na coleta), rode com o modo de diagnóstico:
```
SEFAZ_NFE_DEBUG=1 ./sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx AM SERVICO
```
Esse modo é só para uso manual. O Zabbix junta stdout e stderr no valor do item, então não ative essa variável no servidor.

# Debian / Ubuntu
```sh
apt install python3 python3-requests python3-bs4
```

Ou, com o pip:
```
pip3 install -r requirements.txt
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
- 5: ⚪SEM DADOS (o portal não informa status para o serviço)

### O resultado sem erro para TEMPO.MED
- 1: 🟢DISPONIVEL (menos de 200 ms)
- 2: 🟡INTERMITENTE (de 200 a 999 ms)
- 0: 🔴CRITICO (1000 ms ou mais)
- 5: ⚪SEM DADOS

### Erro na coleta (qualquer STATUS)
- 3: ⚠️ERRO NA COLETA: portal inacessível, tempo esgotado ou layout da página mudou. O template tem um trigger para 3 erros seguidos.

### Tempo de resposta
O portal costuma levar de 4 a 10 s para responder. O script tem limite de 25 s, e os itens do template usam timeout de 30 s. Se você mudar um desses valores, o timeout do item precisa continuar maior que o limite do script.

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
