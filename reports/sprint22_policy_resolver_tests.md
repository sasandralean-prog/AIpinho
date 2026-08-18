# Sprint 22 - Policy Resolver Tests

Gerado em: 2026-06-25 08:22:50

Veredito: SPRINT22_OPERATION_CONTRACT_REQUIRES_PATCH

## generated_at
2026-06-25 08:22:50

## test_commands
[
  "python -m py_compile src\\aipinho\\services\\governance\\operation_contract_service.py src\\aipinho\\schemas\\governance\\operation_contract.py src\\aipinho\\services\\chat\\chat_service.py src\\aipinho\\api\\routers\\continue_integration_router.py -> passed",
  "python -m pytest tests\\unit\\test_operation_contract_service.py tests\\integration\\test_chat_api.py tests\\integration\\test_continue_openai_compat_api.py -q -> 47 passed in 50.47s"
]

## result
47 passed

## regression_points
[
  "aliases normalize write_files to create_file/modify_file",
  "negative constraints deny write/artifact actions before permission ask",
  "forbidden workspace yields denied reason_code",
  "chat write and shell expose operation_contract in contract_preview",
  "Continue exposes operation_contract in aipinho metadata for side-effect approval requests"
]
