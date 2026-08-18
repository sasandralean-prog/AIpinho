# G23 - Capability Truth

Checkpoint: G23_CAPABILITY_TRUTH_READY

Perguntas sobre capacidade operacional agora sao roteadas para CapabilityTruthService, nao para ChatService/LLM generico.

Comportamento validado:

- Perguntas como "voce consegue executar tarefas?" e "voce pode criar projeto?" retornam CAPABILITY_TRUTH_READY.
- A resposta declara capacidade governada sem exagerar: preview, approval e execucao dependem de workspace, policy, plano, runtime e validacao.
- O content provider generico nao pode negar falsamente capacidades governadas.

Evidencia:

- tests/governance/test_g23_capability_truth.py
- tests/governance/test_g26_multichannel_firetest.py
- Matriz ampliada: 46 passed in 132.13s.

