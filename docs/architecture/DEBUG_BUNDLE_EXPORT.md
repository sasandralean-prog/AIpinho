# Debug Bundle Export

`POST /api/v1/debugger/export` gera um artifact JSON sanitizado para revisao tecnica.

O export pode incluir:

- dashboard multiagente;
- state consistency;
- eventos sanitizados;
- trace graph de um run especifico.

Garantias:

- token nao vai na URL;
- raw nao e exposto por padrao;
- secrets sao redigidos;
- artifact exige download autenticado;
- o bundle nao aplica reparos nem altera workspace.

Uso esperado:

1. usuario ou supervisor solicita export;
2. backend cria artifact protegido;
3. UI mostra link/botao de download;
4. revisao externa usa o bundle como evidencia.
