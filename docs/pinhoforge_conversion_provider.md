# PinhoForge Conversion Provider no AIpinho

O AIpinho integra o provider de conversao do PinhoForgeStudio2 pelo Tool Gateway. O backend Python nao tenta reimplementar conversao: ele valida o resultado vindo do provider e registra o output como artifact tokenizado.

## Ferramentas registradas

- `pinhoforge_conversion_list_capabilities`
- `pinhoforge_conversion_dry_run`
- `pinhoforge_conversion_execute`

## Fluxo

1. Tool Gateway cria invocation e avalia policy.
2. Provider lista, faz dry-run ou valida um output de conversao.
3. Em `execute`, um output validado do bridge e obrigatorio.
4. O artifact e registrado pelo `AgentToolGatewayService`.
5. O download continua tokenizado e sem token em URL.

## Seguranca

- Escopo de origem precisa estar na config.
- Output validado e obrigatorio para artifact.
- Conversao semantica/experimental fica desabilitada por config ate existir policy propria.
- Raw fica oculto por padrao.
- Nenhum path/projeto/prompt especifico e usado como regra.
