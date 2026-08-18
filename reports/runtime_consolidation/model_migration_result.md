# Model Migration Result

Data: 2026-08-12

## Resultado

Migração concluída.

`C:\Dev\AI\models` agora é uma junction para:

```text
D:\AI\models
```

Nenhuma configuração da AIpinho foi alterada. FireTest e waves não foram executados.

## Origem e Destino

- Origem original: `C:\Dev\AI\models`
- Destino novo: `D:\AI\models`
- Caminho compatível preservado: `C:\Dev\AI\models`
- Tipo final de `C:\Dev\AI\models`: Junction
- Target final: `D:\AI\models`

## Precheck

Relatório de precheck:

```text
reports/runtime_consolidation/model_migration_precheck.md
```

Estado antes da migração:

- `C:\Dev\AI\models` existia como diretório normal.
- `D:\AI\models` não existia.
- C: livre antes: 7.180.689.408 bytes, aproximadamente 6,69 GiB.
- D: livre antes: 416.243.970.048 bytes, aproximadamente 387,66 GiB.
- Processos Python detectados antes da cópia: nenhum.

## Cópia

Comando executado:

```text
robocopy "C:\Dev\AI\models" "D:\AI\models" /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /MT:8
```

Resultado:

- Robocopy exit code: 1
- Interpretação: sucesso aceitável
- Arquivos copiados: 15
- Falhas: 0
- Bytes copiados: 63.694.530.112
- Tamanho aproximado: 59,32 GiB

## Validação da Cópia

Comparação final:

| Path | Tipo | Arquivos | Bytes | GiB |
|---|---:|---:|---:|---:|
| `C:\Dev\AI\models` | Junction para `D:\AI\models` | 15 | 63.694.530.112 | 59,32 |
| `D:\AI\models` | Diretório destino | 15 | 63.694.530.112 | 59,32 |

Arquivos grandes conferidos por presença/tamanho:

- `qwen2.5-Coder-14B-q5_k_m.gguf` — 10.508.873.152 bytes
- `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` — 8.988.109.984 bytes
- `Qwen2.5-7B-Instruct-Q5_K_M.gguf` — 5.444.831.936 bytes
- `DeepSeek-R1-Distill-Qwen-7B-Q5_K_M.gguf` — 5.444.831.200 bytes
- `starcoder2-7b-Q5_K_M.gguf` — 5.124.832.064 bytes

Hashes SHA256 amostrados:

| Arquivo | Match C:/D: | SHA256 |
|---|---:|---|
| `qwen2.5-Coder-14B-q5_k_m.gguf` | true | `CC64743A6E9867EEB4FA7FFA756BA67F41F10B3B8F3D529AD12402552F0BF796` |
| `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` | true | `67A7933CF2AD596A393C8E13B30BC4DA2D50B283E250B78554AED18817ECA31C` |
| `Qwen2.5-7B-Instruct-Q5_K_M.gguf` | true | `2E998D7E181C8756C5FFC55231B9EE1CDC9D3ACEC4245D6E27D32BD8E738C474` |

## Junction

Procedimento executado:

1. `C:\Dev\AI\models` foi renomeado para `C:\Dev\AI\models.__old_before_junction`.
2. Junction criada:

```text
mklink /J "C:\Dev\AI\models" "D:\AI\models"
```

Validação:

- `C:\Dev\AI\models` aparece como `Directory, ReparsePoint`.
- `LinkType`: `Junction`.
- `Target`: `D:\AI\models`.
- O caminho antigo lista os 15 arquivos esperados.

## Smoke Test

Teste mínimo executado:

```text
python -m pytest tests/unit/test_local_model_path_service.py tests/unit/test_model_path_validator.py -q
```

Resultado:

```text
4 passed in 0.49s
```

Esse smoke test validou o serviço de path local e o validator usando path registrado em:

```text
C:\Dev\AI\models\Qwen2.5-Coder-7B-Instruct.Q4_K_M.gguf
```

Não foi executada inferência real de LLM.

## Liberação de Espaço

Após validação da cópia, junction e smoke test, o usuário autorizou explicitamente a remoção do diretório antigo.

Removido:

```text
C:\Dev\AI\models.__old_before_junction
```

Não removido:

```text
C:\Dev\AI\models
```

porque esse caminho agora é a junction compatível para `D:\AI\models`.

## Espaço Livre Final

- C: livre final: 70.871.871.488 bytes, aproximadamente 66,00 GiB.
- D: livre final: 352.548.827.136 bytes, aproximadamente 328,35 GiB.

## Riscos Restantes

- Se algum processo externo resolver junctions de forma incomum, pode exibir o target em D:, mas o path antigo está preservado para chamadas normais.
- Não foi executado teste de inferência real para evitar carga pesada e porque o objetivo era validar path/cópia/junction.
- Backups fora de `C:\Dev\AI\models.__old_before_junction`, se existirem em outro lugar, não foram alterados.
