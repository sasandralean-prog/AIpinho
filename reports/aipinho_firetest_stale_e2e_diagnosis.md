# AIpinho Workspace Read-only Audit

- Tipo: `workspace_readonly_audit`
- Data/hora UTC: `2026-06-21T22:14:28.948489+00:00`
- Workspace: `C:\Dev\AIpinho`
- Metodo: varredura textual read-only + escrita governada do relatorio.
- Side effects no workspace: apenas este relatorio em caminho solicitado.

## Termos de busca

- `Diagnostique`
- `E2E`
- `C:\Dev\AIpinho`
- `reports/aipinho_firetest_stale_e2e_diagnosis.md`

## Arquivos candidatos encontrados

- `README.md` linha 45 termos: C:\Dev\AIpinho
  - Excerpt sanitizado: ence beyond file placeholders. - Task runtime execution. - Patch apply runtime.  ## Install  ```powershell cd C:\Dev\AIpinho python -m pip install -e .[test] ```  ## Run API  ```powershell cd C:\Dev\AIpinho python -m uvicorn aipinho.m
- `README_FIRST_RUN.md` linha 3 termos: C:\Dev\AIpinho
  - Excerpt sanitizado: # AIpinho RC3 - First Run  Use these commands from `C:\Dev\AIpinho`.  ## Start  ```powershell powershell -ExecutionPolicy Bypass -File scripts\start_aipinho.ps1 ```  ## Check S
- `apps/launcher/README.md` linha 8 termos: C:\Dev\AIpinho
  - Excerpt sanitizado: no projeto, ser leve e permitir empacotamento com PyInstaller.  ## Rodar em desenvolvimento  ```powershell cd C:\Dev\AIpinho .\scripts\dev\start_launcher_desktop.ps1 ```  ## Empacotar .exe  ```powershell cd C:\Dev\AIpinho .\scripts\pa

## Recomendacao segura

- Use este relatorio como indice de auditoria; qualquer alteracao deve passar por task/patch/approval/validation.
- Evite expectativas fixas por projeto/path/modelo. Prefira policy ativa, perfil de teste explicito e fixtures parametrizadas.

## Solicitacao original

Diagnostique os testes E2E obsoletos no workspace C:\Dev\AIpinho e gere reports/aipinho_firetest_stale_e2e_diagnosis.md. Nao altere arquivos fora deste relatorio.
