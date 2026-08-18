# PinhoForge Command Catalog Provider no AIpinho

O provider de catalogo de comandos do PinhoForgeStudio2 entra no AIpinho como fonte read-only para busca e preview. Ele nao executa comandos.

## Ferramentas registradas

- `pinhoforge_command_search`
- `pinhoforge_command_preview`
- `pinhoforge_command_execute`

`pinhoforge_command_execute` existe apenas para retornar bloqueio estruturado. Execucao real continua passando pelo shell governado oficial.

## Politicas

- Busca esconde comandos perigosos por padrao.
- Preview rejeita parametros com risco de injecao.
- Itens retornam `execution_enabled=false`.
- Risco ausente ou desconhecido vira bloqueado.
- Nenhum comando e enviado ao shell por esse provider.

## Uso esperado

O AIpinho pode consultar o catalogo para sugerir um comando seguro, explicar risco e orientar proximo passo. Se o usuario quiser executar, a acao deve ser transformada em uma solicitacao separada ao shell governado com policy, approval e audit.
