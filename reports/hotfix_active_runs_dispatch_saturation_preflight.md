# Hotfix Active Runs Dispatch Saturation - Preflight

- generated_at: 2026-06-25T02:07:34.772582+00:00
- evidence_root: C:\Dev\AIpinho\data\runtime\agent_kernel
- total_runs: 215
- active_runs_effective: 19
- stale_active_runs: 19
- total_sessions: 213
- active_sessions_not_archived: 196
- stale_sessions_over_24h: 196

## Active Runs

| run_id | agent | session | status | operation | last_event | age_s | stale_reasons |
|---|---|---|---|---|---|---:|---|
| agent_run_d84b1a82f89c4dbc8ad0558faef00780 | gemini | agent_session_d1cbe966ee8140c68474a70a662d30e5 | created | gemini_chat | gemini_memory_candidate_created | 919028 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_08eba3644c43479dbd167ca08de95a16 | gemini | agent_session_3a705f2e964141b2970c2b59ccfbb3da | created | gemini_chat | gemini_memory_candidate_created | 918976 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_e8facf73c9844703a35182e21e303201 | gemini | agent_session_7bcb66bd372744299cffeebcfd7e46d8 | created | gemini_chat | gemini_memory_candidate_created | 915811 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_28566830743f4ce4b73a96d1bf0f4ccd | gemini | agent_session_ccb545d58b774537b2161c35565f68f4 | created | gemini_chat | gemini_memory_candidate_created | 864910 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_d061c1c0ff61447ab000f8e3f944bbd1 | gemini | agent_session_0407ede2a55f449eac90fca2d07a93c9 | created | gemini_chat | gemini_memory_candidate_created | 861110 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_694122b9c65349b586dc7b8be08bf056 | gemini | agent_session_ca537ad85afb4cb4bb502370425f0db6 | created | gemini_chat | gemini_memory_candidate_created | 859314 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_5223bd7c701040a2950c3819ac05098b | gemini | agent_session_ab1ae58dbbd54ab1b687f82dcb78b71c | created | gemini_chat | gemini_memory_candidate_created | 858534 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_47ed8cfb717240479c1dcac34e16dcaf | gemini | agent_session_55bd69eca2f3445ca9cb93b2cbe290f9 | created | gemini_chat | gemini_memory_candidate_created | 818076 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_fb5f7bcf3a8b4990b77a99604a73c849 | gemini | agent_session_cddc5398d394418587b2fc20da16e487 | created | gemini_chat | gemini_memory_candidate_created | 782478 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_6c5e6d506c094bf79587db8bf96bfffd | gemini | agent_session_18d8767f2365446594a0ebafc2e3d8b9 | created | gemini_chat | gemini_memory_candidate_created | 544948 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_a9aefa24147c4836b87b9dce8278ab5e | aipinho | chat_2e175734726b49b3bc36af5c6da1db5e | running | patch_pipeline | agent_run_created | 260482 | active_run_without_recent_event_1h |
| agent_run_14ef585ba9c944788a9d7fdcd9f986b3 | aipinho | chat_2e175734726b49b3bc36af5c6da1db5e | running | patch_pipeline | agent_run_created | 258356 | active_run_without_recent_event_1h |
| agent_run_7656f8a30d844f8d8a838a6e0fb9a9b4 | aipinho | agent_session_977a150472e7440d8c61b289aa7a62b7 | running | patch_pipeline | agent_run_created | 257140 | active_run_without_recent_event_1h |
| agent_run_4303e220544d43fea897b85c2d405cf8 | aipinho | agent_session_1b06e925235a4ea793263a4d61efbab4 | running | patch_pipeline | agent_run_created | 257035 | active_run_without_recent_event_1h |
| agent_run_5f3a7a33a064432a8d83d930a033e0d1 | aipinho | agent_session_4e86f36300984aaebb43bb3d02a71ff0 | running | patch_pipeline | agent_run_created | 256461 | active_run_without_recent_event_1h |
| agent_run_d4a2ea6ee2194baeb56d90f930788f83 | aipinho | agent_session_3910d8755c4041ec94e81d0fbb0af837 | running | patch_pipeline | agent_run_created | 256392 | active_run_without_recent_event_1h |
| agent_run_f21a2eeb9ba54220a752488eec0d752d | aipinho | agent_session_0930e136a21a4b32859947d190c798fd | running | patch_pipeline | agent_run_created | 255654 | active_run_without_recent_event_1h |
| agent_run_5e6b25fcb72148d5bdae1dd07759c08e | gemini | agent_session_a371298aeb8f404c81ed009156672d2f | created | gemini_chat | gemini_memory_candidate_created | 168761 | active_run_without_recent_event_1h, active_effective_status_with_completed_at |
| agent_run_65aeb22b35d747018467c6b05581540b | codex | agent_session_49423de13f4f4b4385aa517b70aa3362 | running | codex_chat | memory_candidate_created | 167075 | active_run_without_recent_event_1h |

## Stale Sessions Sample

- gemini / agent_session_185cd36c97c444c7900247471a0ceb38 updated_at=2026-06-13T17:59:57+00:00 age_s=979657 title=Gemini bridge de785d6d
- aipinho / agent_session_78f2b61680554edd86d1432b52c0d1eb updated_at=2026-06-13T21:42:52+00:00 age_s=966282 title=Delegated from lucio
- gemini / agent_session_1d6b2581a03f46c7a61ad0c3e932ad0b updated_at=2026-06-13T18:10:28+00:00 age_s=979026 title=Gemini bridge fc999c14
- aipinho / agent_session_d24f43a5784f4a688e23ce6e9648e282 updated_at=2026-06-13T21:42:52+00:00 age_s=966282 title=Delegated from lucio
- gemini / agent_session_b279e2d4cc6c47c2a5a4b5eb41c848ac updated_at=2026-06-13T21:42:52+00:00 age_s=966282 title=Gemini bridge 1f77d59e
- aipinho / agent_session_2183a841ce4e43cb9288126acd11da7f updated_at=2026-06-13T21:42:52+00:00 age_s=966282 title=Delegated from gemini
- aipinho / agent_session_f40eb6faf6b84d48ba841b69805a69c2 updated_at=2026-06-13T21:42:52+00:00 age_s=966282 title=AIpinho Chat governed write
- aipinho / agent_session_a9967d73eefd4f019dff4bb90365ad40 updated_at=2026-06-13T19:41:16+00:00 age_s=973578 title=AIpinho Chat governed write
- aipinho / agent_session_13c1cf9e4a4c40b58fe2f455cdee9877 updated_at=2026-06-13T20:25:19+00:00 age_s=970935 title=AIpinho Chat governed write
- aipinho / agent_session_b8dd48ad70264bc79d077c72f951c4e2 updated_at=2026-06-13T20:26:58+00:00 age_s=970836 title=AIpinho Chat governed write
- aipinho / agent_session_33f3776980af4c5494f0484a9543c75e updated_at=2026-06-13T20:27:44+00:00 age_s=970790 title=AIpinho Chat governed write
- aipinho / agent_session_bb54e7cb28a24e23aae790985b484748 updated_at=2026-06-13T20:40:07+00:00 age_s=970047 title=AIpinho Chat governed write
- aipinho / agent_session_d531275af08249fa80344ac15cf58f2e updated_at=2026-06-13T20:40:10+00:00 age_s=970044 title=AIpinho Chat governed write
- codex / agent_session_68b47e26e11b40d191d202e0c7dd2b11 updated_at=2026-06-14T01:10:37+00:00 age_s=953817 title=Codex bridge 98f4d083
- aipinho / agent_session_1c34fc646df341098623d881245afb18 updated_at=2026-06-13T23:04:22+00:00 age_s=961392 title=Sprint 20 Dogfood
- gemini / agent_session_d1cbe966ee8140c68474a70a662d30e5 updated_at=2026-06-14T10:50:26+00:00 age_s=919028 title=Gemini bridge c505b592
- gemini / agent_session_3a705f2e964141b2970c2b59ccfbb3da updated_at=2026-06-14T10:51:18+00:00 age_s=918976 title=Gemini bridge c505b592
- gemini / agent_session_eee45f53ac094456814510926243f032 updated_at=2026-06-22T15:21:23+00:00 age_s=211571 title=Gemini bridge c505b592
- aipinho / agent_session_96358935b58f4e549b28774b13360266 updated_at=2026-06-22T15:21:24+00:00 age_s=211570 title=Delegated from gemini
- codex / agent_session_7b84757d87074a328a40932c222d531d updated_at=2026-06-22T15:21:23+00:00 age_s=211571 title=Codex bridge 668a7759
- gemini / agent_session_7bcb66bd372744299cffeebcfd7e46d8 updated_at=2026-06-14T11:44:03+00:00 age_s=915811 title=Gemini bridge c505b592
- aipinho / agent_session_96b1813cfb174936a790357c46f18f57 updated_at=2026-06-14T12:15:49+00:00 age_s=913905 title=skill smoke
- aipinho / agent_session_7d7831d9cc3847a0bae683c65b5223bd updated_at=2026-06-22T15:21:23+00:00 age_s=211571 title=skill smoke
- aipinho / agent_session_4af0a480896f41d8b24cbdd3211afc7a updated_at=2026-06-14T12:17:40+00:00 age_s=913794 title=skill smoke
- aipinho / agent_session_715c65975db14fd7baa31363a0f9c8de updated_at=2026-06-14T12:20:49+00:00 age_s=913605 title=skill test
- aipinho / agent_session_35b6dbf0cfbd4add95afe854f011762e updated_at=2026-06-14T12:20:49+00:00 age_s=913605 title=skill test
- aipinho / agent_session_4e46b76fbb1646bd84ab61a24f7b45aa updated_at=2026-06-14T12:20:49+00:00 age_s=913605 title=skill test
- aipinho / agent_session_0d8faa3440f340a883de548b3dfa6a17 updated_at=2026-06-14T12:20:50+00:00 age_s=913604 title=skill test
- aipinho / agent_session_eeedf13606684fad8e8881d4e6583296 updated_at=2026-06-14T12:24:39+00:00 age_s=913375 title=skill test
- aipinho / agent_session_50b7eef2769f4398ad8f1a483461fac1 updated_at=2026-06-14T12:24:39+00:00 age_s=913375 title=skill test