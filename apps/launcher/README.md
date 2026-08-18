# AIpinho Desktop Launcher

Launcher desktop Windows para operar a AIpinho como cockpit governado. A stack atual e Python + Tkinter/ttk, escolhida por ja existir no projeto, ser leve e permitir empacotamento com PyInstaller.

## Rodar em desenvolvimento

```powershell
cd C:\Dev\AIpinho
.\scripts\dev\start_launcher_desktop.ps1
```

## Empacotar .exe

```powershell
cd C:\Dev\AIpinho
.\scripts\package_launcher_desktop.ps1
```

O executavel esperado e:

```text
C:\Dev\AIpinho\dist\AIpinhoLauncher.exe
```

## Segurança

- O launcher consome endpoints governados existentes.
- Token local e enviado apenas via header Authorization.
- Raw fica oculto por padrao.
- Download de artifact usa ArtifactClient, sem token na URL.
- Restart de 9099 e bloqueado no client; 9099 deve ser tratado por mecanismo externo.
- O launcher nao executa shell, git, patch ou comandos arbitrarios.

## Abas

- Dashboard: status de servicos e restart permitido.
- Chat: modo normal humano, detalhes e raw sanitizado sob acao explicita.
- Pipeline: task/approval reais vindos do backend.
- Debugger 2.0: eventos tecnicos sanitizados.
- Artifacts: inspecao/download por artifact_id real.
- Configuracoes: host, token local, perfis e comandos ADB.
