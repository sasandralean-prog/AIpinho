# Sprint 25 — Capability Matrix

| Capability | Provider | Model | Status policy |
|---|---|---|---|
| text_chat | continue_adapter | aipinho-local | enabled |
| code_assist | continue_adapter | aipinho-local | enabled |
| planning | aipinho_internal | policy_deterministic | enabled |
| intent_classification | aipinho_internal | prompt_intelligence | enabled |
| policy_reasoning | aipinho_internal | policy_kernel | enabled |
| embeddings | local_embedding_runtime | qwen3_embedding_4b_q5_k_m | enabled, health verified by VectorRAG status |
| reranker | local_reranker_runtime | qwen3_reranker_4b_q5_k_m | enabled, health verified by VectorRAG status |
| ocr | tesseract | null | disabled |
| vision | disabled | null | disabled |
| workspace_search | aipinho_internal | keyword_search | enabled with keyword fallback |
| file_summarization | continue_adapter | aipinho-local | enabled |
| patch_planning | aipinho_internal | patch_planning_service | enabled |
| shell_planning | aipinho_internal | governed_shell_policy | enabled |
| artifact_summary | aipinho_internal | artifact_summary | enabled |
