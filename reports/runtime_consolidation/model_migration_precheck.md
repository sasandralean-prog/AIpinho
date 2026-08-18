# Model Migration Precheck

Data: 2026-08-12

## Objetivo

Mover `C:\Dev\AI\models` para `D:\AI\models` preservando compatibilidade por junction em `C:\Dev\AI\models`.

## Regras Aplicadas

- Configs da AIpinho não serão alteradas.
- FireTest e waves não serão executados.
- Nada será deletado antes de cópia, validação e junction.
- A pasta `C:\Dev\AI\models` não será apagada depois da junction.
- Se houver limpeza posterior, o único alvo permitido será `C:\Dev\AI\models.__old_before_junction`.

## Estado da Origem

- Origem: `C:\Dev\AI\models`
- Existe: sim
- Tipo atual: diretório normal, não junction
- Contagem de arquivos: 15
- Tamanho total: 63.694.530.112 bytes
- Tamanho total aproximado: 59,32 GiB

## Estado do Destino

- Destino: `D:\AI\models`
- Existe antes da migração: não
- Ação esperada: `robocopy` criará o destino.

## Espaço Livre

- C: livre antes da migração: 7.180.689.408 bytes, aproximadamente 6,69 GiB
- D: livre antes da migração: 416.243.970.048 bytes, aproximadamente 387,66 GiB

## Amostra de Arquivos Grandes

- `qwen2.5-Coder-14B-q5_k_m.gguf` — 10.508.873.152 bytes
- `DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf` — 8.988.109.984 bytes
- `Qwen2.5-7B-Instruct-Q5_K_M.gguf` — 5.444.831.936 bytes
- `DeepSeek-R1-Distill-Qwen-7B-Q5_K_M.gguf` — 5.444.831.200 bytes
- `starcoder2-7b-Q5_K_M.gguf` — 5.124.832.064 bytes

## Processos Python

Nenhum processo `python.exe` ou `pythonw.exe` foi detectado no momento do precheck.

## Decisão

Precheck aprovado para cópia com `robocopy`.
