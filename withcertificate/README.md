# Monitoramento da Sefaz com Zabbix e Grafana

## Visão Geral

Este repositório contém templates para monitoramento do sistema SEFAZ usando Zabbix e exibição dos dados utilizando Grafana. Os templates do Zabbix incluem cenários web para cada URL da SEFAZ que está sendo monitorada, com cada cenário web correspondendo a um estado brasileiro. Na aba de autenticação de cada cenário web, é necessário inserir o nome do arquivo de certificado SSL e do arquivo de chave SSL para acessar as URLs da SEFAZ. Por padrão, os nomes desses arquivos são:

- sefaz_cert.pem
- sefaz_cert.key

No Grafana, o plugin Grafana-worldmap-panel deve ser instalado. Uma vez instalado, o dashboard pode ser importado e exibirá as coordenadas de geolocalização de cada estado do Brasil a partir de um arquivo JSON neste repositório.

Para configurar os arquivos de certificado SSL e chave SSL no servidor Zabbix, siga estas etapas:

1. **Localize o arquivo de configuração do Zabbix Server:**

   O arquivo de configuração do servidor Zabbix geralmente está localizado em `/etc/zabbix/zabbix_server.conf`.

2. **Edite o arquivo de configuração:**

   Abra o arquivo de configuração com um editor de texto, como `nano` ou `vi`:

   ```bash
   sudo nano /etc/zabbix/zabbix_server.conf
	 ```

3. **Adicione ou edite as seguintes linhas:**

   Adicione ou modifique as linhas abaixo com os caminhos dos seus arquivos de certificado e chave SSL:

   ```bash
	TLSCertFile=/caminho/para/sefaz_cert.pem
	TLSKeyFile=/caminho/para/sefaz_cert.key
	 ```

4. **Salve as alterações e saia do editor:**

	No `nano`, você pode salvar e sair pressionando `Ctrl + O` para salvar e `Ctrl + X` para sair.
  No `vi`, você pode salvar e sair pressionando `:w` para salvar, `:q` para sair e `:wq` para salvar e sair .

5. **Reinicie o Zabbix Server:**

	Após fazer as alterações no arquivo de configuração, reinicie o serviço do Zabbix Server para que as alterações entrem em vigor:

   ```bash
	sudo systemctl restart zabbix-server
	 ```

Certifique-se de substituir `/caminho/para/` pelo caminho real onde os arquivos `sefaz_cert.pem` e `sefaz_cert.key` estão localizados.

## Como Usar

Para usar os templates deste repositório, siga estas etapas:

1. Importe os templates do Zabbix.
2. Insira o nome do arquivo de certificado SSL e do arquivo de chave SSL na aba de autenticação de cada cenário web.
3. Instale o plugin Grafana-worldmap-panel.
4. Importe o dashboard do Grafana.
5. Monitore o sistema SEFAZ e visualize os dados no Grafana.

[GIT original](https://github.com/thePaulRichard/zabbix-templates/tree/main/sefaz)