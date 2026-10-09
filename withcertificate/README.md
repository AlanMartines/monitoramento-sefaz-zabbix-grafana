# Monitoramento da Sefaz com Zabbix e Grafana

## Visão Geral

> **Abordagem alternativa, sem manutenção ativa.** Para a maioria dos casos, use o template "Sefaz NF-e Portal" do [README principal](../README.md), que não precisa de certificado. Esta pasta serve para quem quer testar diretamente os webservices de cada SEFAZ com o certificado digital da empresa.

Esta pasta contém o host `Sefaz` (`zbx_export_host_withcertificate.yaml`, formato Zabbix 7.0) com 14 cenários web, um por autorizador. Cada cenário faz uma requisição GET aos webservices da NF-e 4.00 daquele autorizador e espera HTTP 200. Na aba de autenticação de cada cenário web, é necessário inserir o nome do arquivo de certificado SSL e do arquivo de chave SSL para acessar as URLs da SEFAZ. Por padrão, os nomes desses arquivos são:

- sefaz_cert.pem
- sefaz_cert.key

Limitações conhecidas:
- O host não tem triggers. Crie os seus (por exemplo, sobre `web.test.fail[<cenário>]`) se quiser alertas.
- As URLs dos webservices são as de 2019. Confira-as na página de [webservices](https://www.nfe.fazenda.gov.br/portal/webServices.aspx) do portal antes de usar.
- O dashboard `Zabbix - Monitoramento Sefaz.json` usa os painéis antigos `singlestat`, `graph` e `grafana-worldmap-panel`. O Grafana 11 converte esses painéis automaticamente, mas o mapa fica sem fundo ("API KEY REQUIRED"). Troque a camada base do painel Geomap ou remova o mapa.

Para configurar os arquivos de certificado SSL e chave SSL no servidor Zabbix, siga estas etapas:

1. **Localize o arquivo de configuração do Zabbix Server:**

   O arquivo de configuração do servidor Zabbix geralmente está localizado em `/etc/zabbix/zabbix_server.conf`.

2. **Edite o arquivo de configuração:**

   Abra o arquivo de configuração com um editor de texto, como `nano` ou `vi`:

   ```bash
   sudo nano /etc/zabbix/zabbix_server.conf
	 ```

3. **Adicione ou edite as seguintes linhas:**

   Os cenários web procuram o certificado e a chave nos **diretórios** definidos por `SSLCertLocation` e `SSLKeyLocation`. Nos cenários, informe só o nome do arquivo (`sefaz_cert.pem` e `sefaz_cert.key`). Não use `TLSCertFile`/`TLSKeyFile`, que servem para a criptografia entre os componentes do Zabbix.

   ```bash
   SSLCertLocation=/caminho/para/certificados
   SSLKeyLocation=/caminho/para/chaves
   ```

   Se os cenários rodarem num Zabbix Proxy, faça a mesma configuração no `zabbix_proxy.conf`.

4. **Salve as alterações e saia do editor:**

	No `nano`, você pode salvar e sair pressionando `Ctrl + O` para salvar e `Ctrl + X` para sair.
  No `vi`, você pode salvar e sair pressionando `:w` para salvar, `:q` para sair e `:wq` para salvar e sair .

5. **Reinicie o Zabbix Server:**

	Após fazer as alterações no arquivo de configuração, reinicie o serviço do Zabbix Server para que as alterações entrem em vigor:

   ```bash
	sudo systemctl restart zabbix-server
	 ```

Certifique-se de substituir `/caminho/para/...` pelos diretórios reais onde ficam `sefaz_cert.pem` e `sefaz_cert.key`. Os arquivos precisam poder ser lidos pelo usuário `zabbix`.

## Como Usar

Para usar os templates deste repositório, siga estas etapas:

1. Configure `SSLCertLocation`/`SSLKeyLocation` como descrito acima e copie o certificado e a chave para esses diretórios.
2. Importe `zbx_export_host_withcertificate.yaml` no Zabbix 7.0. O grupo `Web Check` é criado se não existir.
3. Se os seus arquivos tiverem outros nomes, ajuste o certificado e a chave na aba de autenticação de cada cenário web.
4. Opcional: importe o dashboard `Zabbix - Monitoramento Sefaz.json` no Grafana (veja as limitações acima).

[GIT original](https://github.com/thePaulRichard/zabbix-templates/tree/main/sefaz)