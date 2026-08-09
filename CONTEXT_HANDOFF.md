# Contexto de sessão — ai-fiscal-rag → Fiscal Compliance Agent

> **Superado em 2026-08-09.** O plano de Fase 1 abaixo (migração de domínio Treasury → rejeição de NF-e/SEFAZ) e tudo que dependia dele (Fases 2–4) foi avaliado em sessão de desenvolvimento subsequente e **rejeitado** — ver `docs/adr/0007-nfe-sefaz-rejection-domain-migration-rejected.md`. Motivo resumido: a premissa central de que o diagnóstico de rejeição de NF-e exigiria um loop agêntico genuíno não se sustentou ao checar mensagens reais de rejeição da SEFAZ (a maioria é resolvível deterministicamente, sem ambiguidade real a investigar). Este arquivo é mantido como registro histórico do raciocínio que levou à Fase 0 (ADRs 0001–0006, que continuam válidos e não são afetados por esta reversão), não como roteiro ativo.

Gerado em 2026-08-09 a partir de uma sessão de planejamento no repositório `career-knowledge` (PKB pessoal, não este código). Este arquivo deve ser colocado na raiz do repositório **ai-fiscal-rag** (ex.: `CONTEXT_HANDOFF.md`) e usado para abrir uma nova sessão de desenvolvimento aqui — não no `career-knowledge`.

## Por que este projeto e não outro

Havia um gap real de portfólio: nenhum projeto pessoal demonstra comportamento agêntico (multi-step reasoning, não só um pipeline retrieve→gerar). Dois candidatos foram avaliados para fechar esse gap — evoluir o `ncm-classifier-ai` ou o `ai-fiscal-rag`. Decisão: **ai-fiscal-rag**, porque:

- O formato do problema já é compatível: falta só a camada de decisão multi-etapa, a infraestrutura de guardrail/confiança/fallback humano já existe.
- O domínio-alvo (rejeição de NF-e/SEFAZ) é o mesmo eixo de raridade profissional (compliance fiscal multi-país) do trabalho na Oracle, sem expor nada proprietário — dado público, análogo ao uso da TIPI pública no `ncm-classifier-ai`.
- `ncm-classifier-ai` é um problema de classificação single-shot; forçar um loop agêntico nele seria artificial.

Consolidar isso em um único projeto evita um sexto projeto disperso no portfólio e resolve o problema real do `ai-fiscal-rag` (parado ~4 semanas, sem ADRs, sem evals) transformando-o na peça mais forte em vez de arquivá-lo.

## Estado real do repositório hoje (verificado via GitHub API em 2026-08-09)

- Último push: 2026-07-11. Topics já preenchidos (rag, n8n, fastapi, gemini, fiscal-data, etc.) — item já resolvido, não repetir.
- **Não é agêntico hoje**: `FiscalRagService.handle_fiscal_search` (`app/fiscal_rag_service.py`) é um pipeline linear fixo — `validate_intent` → (opcional) `identify_country_context` → `search_in_chromadb` → `rerank_results` (Gemini) → `generate_analysis` (Gemini, saída estruturada). Uma única passada, sem ramificação condicionada a resultado intermediário, sem retry de estratégia.
- Domínio atual: câmbio/moeda por país via dados públicos do U.S. Treasury (`app/integrations.py::TreasuryClient`, `app/models.py::ExchangeRate`). Não é fiscal brasileiro.
- Saída estruturada já existe e já tem o campo certo para a migração: `FiscalResponse` (`app/fiscal_response.py`) tem `country`, `error_code`, `technical_analysis`, `confidence`, `sources_used`, `next_action`. **`error_code` já existe no schema e hoje está sempre vazio** — é o campo natural para carregar o código de rejeição SEFAZ identificado. Não precisa quebrar o schema.
- Confidence-gating e human-in-the-loop já existem, mas vivem no **n8n**, não no código Python: o workflow (`n8n/workflow-n8n-triagem-fiscal.json`, documentado em `n8n/README.md`) decide auto-resposta vs. escalação humana comparando `confidence ≥ 0.7` num nó `If`. A API em si não tem esse gate.
- Guardrail de intenção existe e funciona (`GeminiService.validate_intent`), mas é hardcoded para câmbio/fiscal genérico — vai precisar de novo prompt para o domínio de rejeição de NF-e.
- Memória de sessão: em memória, por `session_id` (`app/memory_service.py`) — não persistente, reseta a cada restart. Manter como está; documentar como decisão, não como bug.
- Zero ADRs (`docs/adr` não existe no repo — confirmado 404). Um teste (`tests/test_fiscal_rag_service.py`).
- `CLAUDE.md` já existe no repo (projeto foi desenvolvido com Claude Code) — revisar e atualizar quando a direção mudar, para a próxima sessão não repetir contexto perdido.

## Plano de execução (ordem importa)

### Fase 0 — ADRs retroativos do que já existe (fazer antes de mudar qualquer código)

Documentar as decisões atuais como ADR, no mesmo estilo do `ncm-classifier-ai` e `SmartCondo` (Status/Contexto/Decisão/Consequências, incluindo trade-offs aceitos). Pelo menos:

1. Guardrail de intenção antes do retrieval (`validate_intent`) — por que rejeitar fora de escopo antes de gastar uma chamada de retrieval/LLM.
2. Saída estruturada via Pydantic (`FiscalResponse`) em vez de texto livre.
3. Confidence-gated automation implementada no n8n (não na API) — decisão consciente ou dívida a corrigir? Decidir e documentar.
4. Human-in-the-loop como branch explícito do workflow, não exceção não tratada.
5. Memória de sessão em memória, não persistente — trade-off aceito, não lacuna.
6. Integração de LLM acoplada à Gemini (`GeminiService` fala direto com `google.generativeai`, sem port/adapter) — comparar com a decisão equivalente do `ncm-classifier-ai` (ADR-0016, `LLMClient` agnóstico). Decidir se replica esse padrão aqui ou documenta por que não.

Isso sozinho já tira o projeto do estado "sem documentação arquitetural" antes de qualquer linha de código nova mudar.

### Fase 1 — Migração de domínio (Treasury exchange-rate → rejeição de NF-e/SEFAZ)

- Fonte de dados: tabela pública de códigos de rejeição de NF-e (SEFAZ/Receita Federal — portal nacional da NF-e). **[verificar fonte pública exata e licença de uso antes de ingerir]**, mesmo padrão de due diligence usado para a TIPI no `ncm-classifier-ai`.
- Substituir `TreasuryClient`/`ExchangeRate` (`app/integrations.py`, `app/models.py`) pelo cliente/schema equivalente para a tabela de rejeição.
- Reaproveitar `error_code` em `FiscalResponse` para carregar o código de rejeição identificado (ex.: "204", "539") — não criar campo novo.
- Reescrever os prompts de `GeminiService` (`validate_intent`, `rerank_results`, `generate_analysis`) para o novo domínio.
- Novo ADR: por que migrar o domínio e o que se perde/ganha (a demo de câmbio funcionava e é honesta; documentar isso como precedente, não descartar sem registro).

### Fase 2 — Camada agêntica (o gap real que este projeto precisa fechar)

Hoje o pipeline é fixo. Para virar um agente de verdade — não é preciso LangGraph, mas precisa de decisão condicionada a resultado intermediário — a proposta:

1. **Identificar** o(s) código(s) de rejeição a partir da mensagem bruta de rejeição da NF-e (pode ter mais de um erro embutido).
2. **Recuperar** a regra/orientação de correção para cada código identificado (retrieval sobre a tabela).
3. **Propor** uma correção estruturada e acionável (não só explicação em texto — ex.: "corrigir dígito verificador da chave de acesso", "reenviar dentro de X horas"), aproveitando `next_action` que já existe no schema.
4. **Validar** a correção proposta contra uma checagem determinística (formato de CNPJ, dígito verificador de chave de acesso, formato de NCM referenciado) — mesmo padrão do verification gate do `ncm-classifier-ai` (ADR-0002/ADR-0014), que é a peça que falta hoje aqui.
5. Só then decidir auto-resposta vs. escalação, combinando **dois sinais** (confidence do LLM **e** resultado da checagem determinística), não só confidence como hoje — mover essa lógica para dentro da API (Python), deixando o n8n só orquestrar, não decidir.

Cada etapa acima que falhar ou for rejeitada deve virar ADR com resultado medido, inclusive se a abordagem não funcionar — é o padrão que já validou os outros dois projetos de IA do portfólio (decisões rejeitadas documentadas, sem viés de sobrevivência). Não inflar "agente" se o resultado prático for um pipeline com um `if` a mais — só chamar de agêntico o que de fato ramificar com base em resultado intermediário.

### Fase 3 — Suite de evals

- Dataset rotulado de casos (mensagem de rejeição → código correto → ação correta), mesmo espírito do `eval/run_eval.py` do `ncm-classifier-ai`.
- Métrica de classificação do código (top-1/top-3, como no NCM).
- LLM-as-judge para qualidade da correção proposta em texto livre (não dá para medir "next_action" por exact match).
- Gate de CI que bloqueia regressão de acurácia, com o mesmo cuidado do `ncm-classifier-ai` ADR-0021: separar o que é barato/determinístico de rodar em CI do que exigiria chamada real de LLM (custo recorrente, flakiness).

### Fase 4 — Atualizar o workflow n8n e o README

- Ajustar `n8n/README.md` e o workflow para o novo domínio (hoje fala de câmbio/Treasury).
- Mover o gate de confiança para depender também da checagem determinística da Fase 2, não só do `confidence ≥ 0.7` isolado.
- Reescrever `README.md` do repo (hoje descreve "RAG API for fiscal and exchange-rate questions" — vai ficar errado depois da migração).

## Depois de fechar os maiores gaps: voltar ao `career-knowledge`

Isto é o passo que fica fácil de esquecer porque acontece em outro repositório. Quando as Fases 0–3 acima estiverem substancialmente prontas (domínio migrado, camada agêntica funcionando com resultado medido, evals rodando), voltar ao repositório `career-knowledge` (`D:\repos\career-knowledge`) e atualizar:

1. **`docs/project-portfolio.md`** — reescrever a seção `PROJECT-004 — ai-fiscal-rag` inteira: Objetivo, Problema, Arquitetura, Decisões Arquiteturais (todos os ADRs novos), Tecnologias, Competências demonstradas (adicionar algo como "sistemas agênticos / multi-step reasoning", "verification gate determinístico"), Conceitos importantes, Evidências para entrevistas, Balas de CV. Seguir exatamente o mesmo formato usado nos outros PROJECT-00N — não inventar seção nova.
2. **`docs/profile.md`** — seção "Especialidades" / "IA Aplicada": já lista "Pipelines RAG", "Guardrails determinísticos", "Verification gate" — avaliar se cabe adicionar algo como "Sistemas agênticos" só depois de ter evidência real (não antes, para não inflar). Revisar também "Gaps Conhecidos" — o gap "IA aplicada a produto (não apoio ao desenvolvimento)" citado como motivo de rejeição no JusBrasil pode mudar de status se este projeto tiver um ciclo de feedback real; avaliar honestamente, sem forçar.
3. **`docs/target-companies.md`** — não precisa mudar os critérios (IA aplicada já é peso 3, não gate), mas revisar as anotações de empresas fiscal-tech (Thomson Reuters, Avalara, Vertex, Sovos) se este projeto virar evidência concreta a citar em candidatura.
4. Conferir se `docs/interview-history.md` precisa de nova entrada quando este projeto for citado numa entrevista real e gerar um padrão observado (positivo ou negativo).

Checklist de qualidade antes de fechar a atualização no `career-knowledge` (do próprio `CLAUDE.md` do repo): nenhuma informação duplicada entre arquivos, cada arquivo mantém responsabilidade única, texto resultante igual ou mais enxuto que antes, nenhuma informação relevante perdida (só movida), nomenclatura consistente com os demais documentos.
