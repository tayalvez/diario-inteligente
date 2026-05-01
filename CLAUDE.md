# Instruções para o Agente

## Guia de desenvolvimento

Todas as decisões de código neste projeto seguem o [GUIA_DESENVOLVIMENTO.md](./GUIA_DESENVOLVIMENTO.md).

Pontos essenciais:

- **Português**: use português para nomes de variáveis, funções, classes e comentários. Exceções: termos técnicos sem tradução (`embedding`, `score`, `token`) e convenções de frameworks (`Base`, `Column`, `Depends`).
- **Funções pequenas**: cada função faz uma coisa só.
- **Sem comentários óbvios**: o código deve se explicar pelos nomes. Comente apenas o *por quê*, nunca o *o quê*.
- **Sem código defensivo desnecessário**: não valide o que o sistema interno já garante.
- **Sem abstrações prematuras**: resolva o problema concreto primeiro.

---

## Stack do projeto

- **Backend**: FastAPI + SQLite + SQLAlchemy
- **Frontend**: Angular 21
- **ML**: sentence-transformers (modelo local `paraphrase-multilingual-MiniLM-L12-v2`)

## Estrutura

```
app/
  models/    ← entidades e banco (SQLAlchemy)
  schemas/   ← contratos de entrada/saída (Pydantic)
  api/       ← rotas HTTP (FastAPI)
  services/  ← lógica de aplicação
  ml/        ← similaridade, embeddings, NLP
scripts/     ← utilitários de manutenção (backfill, rebuild)
tests/       ← testes automatizados
frontend/    ← interface Angular
```

---

## Modelo central

`Evento` é a entidade central do sistema:
- `evento` — nome/label (ex: "cansada", "ansiedade")
- `data_hora` — obrigatório
- `energia`, `humor`, `estresse` — floats 0.0–1.0, obrigatórios
- `descricao`, `contexto`, `tags`, `dimensoes_extras` — opcionais
- `embedding` — vetor semântico gerado a partir da descrição

`RelacaoEvento` representa uma aresta do grafo entre dois eventos:
- `intensidade` — força da relação (0.0–1.0), soma das evidências
- `confiabilidade` — 1.0 = criada manualmente, menor = automática
- `motivo` — texto legível explicando por que a relação existe

---

## Conceito central: percepção, não realidade

**Princípio fundamental do sistema**: os dados refletem como o usuário *percebe e registra* suas experiências — não a realidade objetiva dos fatos.

Isso impacta toda a linguagem dos insights, motivos e análises:

- Sempre use "percebido" ou "nos registros": *"bem-estar percebido"*, *"nos seus registros"*, *"padrão nos registros"*.
- Nunca afirme causalidade: *"pilates causa bem-estar"* é errado; *"pilates co-ocorre com bem-estar alto nos registros"* é correto.
- Nunca afirme que um padrão nos registros representa a realidade do usuário.
- Todo insight inclui `interpretacao_confiavel: False` e um aviso explícito de que é baseado nos registros.

**Módulos que implementam esse conceito:**

- `app/ml/perception_bias.py` — viés de percepção: analisa como o usuário registra (viés de valência, de intensidade, de frequência de registro).
- `app/ml/insights_comportamentais.py` — insights comportamentais: tendência recente, padrão horário, co-ocorrências, ciclos, hub emocional, cluster emocional — todos fraseados como padrões *nos registros*.

**Exemplo de linguagem correta:**
```
# Errado
"pilates melhora seu humor"
"você fica triste às segundas"

# Correto
"pilates aparece nos dias em que você registra maior bem-estar percebido"
"segunda é o dia em que você registra os estados mais difíceis nos seus registros"
```

---

## Lógica de similaridade (`app/ml/similaridade.py`)

As relações automáticas são geradas por até quatro fontes de evidência independentes. Cada uma contribui com uma intensidade parcial; a soma forma a intensidade total da relação.

### Fontes de evidência

| Fonte | Condição | Intensidade |
|---|---|---|
| Tags em comum | ≥ 1 tag compartilhada | 0.12 (1 tag) até 0.30 (4+) |
| Título igual ou muito parecido | `norm_a == norm_b` ou SequenceMatcher ≥ 0.88 | 0.18–0.22 |
| 3+ dimensões iguais | `humor`, `energia`, `estresse` dentro de ±0.05 | 0.18–0.30 |
| Descrição similar | ver tabela abaixo | 0.16–0.30 |

### Limiares de descrição

| Condição | Intensidade | Motivo gerado |
|---|---|---|
| sim_texto ≥ 0.95 | 0.30 | descrições com o mesmo sentido/intenção |
| sim_texto ≥ 0.60 | 0.24 | descrições muito parecidas |
| sim_emb ≥ 0.76 | 0.22 | descrições com sentido/intenção parecidos |
| sim_emb ≥ 0.67 **e** sim_texto ≥ 0.35 | 0.16 | descrições semanticamente próximas |

O motivo de descrição sempre inclui as palavras significativas em comum, ex: `descrições semanticamente próximas (palavras em comum: carnage, livro)`.

### Decisões de design — não reverter sem motivo

- **Título**: embedding **não** é usado para comparar títulos. O modelo de embedding confunde domínio (bem-estar, saúde) com similaridade semântica real, gerando pares sem sentido como `pilates ↔ sono` (score 0.83). Apenas igualdade textual e SequenceMatcher são válidos.
- **Tags**: todas as tags são consideradas, incluindo `sentimento` e `obrigatorio`. Não existe lista de tags genéricas a filtrar.
- **Limite de relações**: não há `MAX_RELACOES`. Cada par que passa no `LIMIAR = 0.10` gera uma relação.
- **Dimensões sozinhas**: 3+ dimensões iguais sozinhas **geram** relação (intensidade 0.18). O bloqueio antigo foi removido a pedido.

---

## Embeddings (`app/ml/nlp.py`)

O modelo é carregado localmente. Ordem de prioridade:
1. Variável de ambiente `EMBEDDING_MODEL_DIR` (se apontar para diretório existente)
2. `models/paraphrase-multilingual-MiniLM-L12-v2/` dentro do projeto
3. Download remoto — só se `EMBEDDING_ALLOW_REMOTE_DOWNLOAD=1`

Para baixar o modelo pela primeira vez:
```bash
venv/bin/python3 scripts/download_embedding_model.py
```

---

## Scripts de manutenção

Após qualquer alteração na lógica de similaridade, rodar:
```bash
venv/bin/python3 scripts/rebuild_auto_relations.py
```

Para gerar embeddings em eventos que ainda não têm:
```bash
venv/bin/python3 scripts/backfill_embeddings.py
```

O `rebuild_auto_relations.py` é idempotente: preserva relações manuais (`confiabilidade >= 1.0`), remove automáticas obsoletas e cria/atualiza as que passam nas heurísticas atuais.

---

## Testes

```bash
venv/bin/python3 -m unittest tests.test_similaridade tests.test_nlp_config -v
```

Rodar sempre após alterar `app/ml/similaridade.py` ou `app/ml/nlp.py`.
