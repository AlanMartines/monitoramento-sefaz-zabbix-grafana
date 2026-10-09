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

### Modo JSON
```
./sefaznfe.py https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx JSON
```
Lê o portal uma vez e devolve todos os autorizadores:
```json
{"dados": {"AM": {"AUTORIZACAO": 1, "RETORNO.AUT": 1, ..., "TEMPO.MED": 5}, "BA": {...}}}
```
`TEMPO.MED.MS` (tempo médio em ms) só aparece quando o portal informa o valor. `GERAL` é o pior status entre os 7 serviços. Em caso de falha, a saída é `{"erro": "<motivo>"}`.

# Como Usar

## Template "Sefaz NF-e Portal" (recomendado)
Arquivos: `zbx_export_template_portal.yaml` e `zbx_export_host_portal.yaml`. Requer Zabbix 7.0.

1. Importe `zbx_export_template_portal.yaml` e depois `zbx_export_host_portal.yaml`.
2. Pronto: o host **Sefaz NF-e Portal** lê o portal **uma vez por minuto** e descobre sozinho os autorizadores listados (AM, BA, GO, MG, MS, MT, PE, PR, RS, SP, SVAN, SVRS, SVC-AN, SVC-RS).

Como funciona:
- **Item mestre** `sefaznfe.py[{$SEFAZ.URL},JSON]`: uma única execução do script por intervalo, em vez de uma por serviço e por estado.
- **Descoberta (LLD)**: cria, para cada autorizador, os 8 itens de status, o "Status geral" (pior serviço, usado no mapa), o tempo médio em ms e os triggers. Um autorizador que sai do portal é removido após 30 dias.
- **Alertas com confirmação**: offline/crítico (HIGH) e instável/intermitente (AVERAGE) só disparam após **3 leituras seguidas**.
- **Falha na coleta**: se o script não conseguir ler o portal três vezes seguidas, ou parar de enviar dados por 10 minutos, dispara um único alerta, "Sefaz NF-e: falha na coleta do portal". Os itens de status mantêm o último valor, e os demais triggers dependem desse, então não há avalanche de alertas.

Macros do template:

| Macro | Padrão | Uso |
|---|---|---|
| `{$SEFAZ.URL}` | `https://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx` | Página consultada |
| `{$SEFAZ.INTERVALO}` | `1m` | Intervalo de leitura |

## Template legado (um host por autorizador)
Arquivos: `zbx_export_templates.yaml` e `zbx_export_hosts.yaml`. Funciona, mas executa o script 8 vezes por host a cada 2 minutos (cerca de 120 execuções). Mantido porque o dashboard do Grafana ainda usa esses hosts. O host `SEFAZ_CE` não tem linha no portal (o CE é atendido pelo SVRS) e retorna 3.

## Grafana
Requer o plugin [Zabbix](https://grafana.com/grafana/plugins/alexanderzobnin-zabbix-app/) com um datasource configurado.

- **`Sefaz NF-e Portal.json` (recomendado)**: para o template "Sefaz NF-e Portal". A variável **Autorizador** é preenchida a partir dos itens descobertos no Zabbix, e um painel é repetido para cada autorizador, então novos autorizadores aparecem sozinhos. O dashboard também mostra o status da coleta, o histórico do Status Serviço e o tempo médio em ms. Na importação, escolha o datasource Zabbix.
- **`Sefaz NF-e Mapa.json`**: o mesmo layout do [dashboard com certificado](https://grafana.com/grafana/dashboards/10005-zabbix-monitoramento-sefaz/), mas sem certificado, usando o template "Sefaz NF-e Portal" (veja abaixo).
- **`Consultar Disponibilidade NF-e Sefaz.json` (legado)**: para os hosts do template legado, com um painel por serviço e por estado.

### Dashboard "Sefaz NF-e Mapa" (sem certificado)
- **Mapa do Brasil**: um ponto por autorizador, colorido pelo pior status entre os serviços (item "Status geral"). Um círculo translúcido aparece quando há problema: maior e vermelho para offline, menor e amarelo para instável. SVAN e SVC-AN ficam em Brasília, SVRS e SVC-RS em Porto Alegre.
- **Para o autorizador escolhido**, uma linha por serviço com:
  - o status atual (OK, Instável, Offline);
  - um gauge com a **disponibilidade %** no período (fração das leituras em verde);
  - o **histórico** do status.
- **Rodapé**: quais UFs usam cada autorizador virtual.

Diferença para o dashboard com certificado: o portal não informa o tempo de resposta de cada serviço. Por isso, os gauges e gráficos mostram disponibilidade e histórico, não milissegundos.

**Instalação (uma vez):** o mapa precisa do arquivo de coordenadas `grafana/sefaz-autorizadores.json` no servidor do Grafana. O Grafana não carrega esse arquivo de uma URL externa.
```sh
# Grafana instalado por pacote
sudo cp grafana/sefaz-autorizadores.json /usr/share/grafana/public/gazetteer/

# Grafana em Docker: monte o arquivo como volume
#   -v /caminho/grafana/sefaz-autorizadores.json:/usr/share/grafana/public/gazetteer/sefaz-autorizadores.json:ro
```
Confira o arquivo depois de atualizar o Grafana. O fundo do mapa (Esri Light Gray) é carregado pelo navegador e precisa de acesso à internet.

**Itens novos no Grafana:** o plugin Zabbix guarda a lista de itens em cache por até 1 hora. Depois de importar ou atualizar o template, os itens novos (como "Status geral") podem demorar a aparecer, a menos que você reinicie o Grafana ou reduza o *Cache TTL* do datasource.

## Com certificado digital
A pasta [withcertificate](withcertificate/README.md) tem uma abordagem alternativa, sem manutenção ativa: cenários web que chamam diretamente os webservices de cada SEFAZ usando o certificado digital da empresa.

# Desenvolvimento
```
pip install -r requirements.txt pytest pyyaml ruff
ruff check .
pytest tests
```
Os testes usam a tabela real do portal salva em `tests/fixtures/` e não acessam a rede. O CI roda em Python 3.8 e 3.12.

# Testado com
- Zabbix: v7.0 (7.0.31)
- Grafana: v11 (11.6.0), plugin Zabbix 6.9.1

# [Downgrade para Zabbix v5.4 (apenas template legado):](https://github.com/AlanMartines/monitoramento-sefaz-zabbix-grafana/issues/2#issue-2629057062)
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
