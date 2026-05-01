# Regras de Negócio — Diário de Autoconhecimento

---

## 1. Princípio fundamental

**Os dados refletem como o usuário percebe e registra suas experiências — não a realidade objetiva.**

Toda análise, insight e linguagem do sistema parte desse princípio. Nunca se afirma causalidade; sempre se fala em co-ocorrência nos registros. Todo insight inclui `interpretacao_confiavel: false`.

Exemplos de linguagem correta:
- ✅ "pilates aparece nos dias em que você registra maior bem-estar percebido"
- ✅ "segunda é o dia em que você registra os estados mais difíceis nos seus registros"
- ❌ "pilates melhora seu humor"
- ❌ "você fica triste às segundas"

---

## 2. Entidade central — `Evento`

Cada registro do usuário é um `Evento`. Um evento representa uma ocorrência percebida e anotada, com label, data/hora e um conjunto de dimensões.

### Campos obrigatórios

| Campo       | Tipo     | Descrição |
|-------------|----------|-----------|
| `evento`    | texto    | Nome/label em minúsculas (ex: "cansada", "pilates") |
| `data_hora` | datetime | Data e hora do registro |
| `energia`   | float    | Nível de energia percebido (0.0–1.0) |
| `humor`     | float    | Humor percebido (0.0–1.0) |
| `estresse`  | float    | Estresse percebido (0.0–1.0) |
| `sensibilidade` | float | Sensibilidade percebida (0.0–1.0) |
| `serenidade`    | float | Serenidade percebida (0.0–1.0) |
| `interesse`     | float | Interesse percebido (0.0–1.0) |

### Campos opcionais

| Campo              | Tipo           | Descrição |
|--------------------|----------------|-----------|
| `descricao`        | texto          | Texto livre sobre o estado |
| `contexto`         | JSON `{k: v}`  | Pares chave-valor (ex: `{"local": "trabalho"}`) |
| `tags`             | JSON `[str]`   | Lista de tags livres |
| `dimensoes_extras` | JSON `{k: float}` | Dimensões customizadas adicionais (ex: `{"foco": 0.9}`) |
| `embedding`        | JSON `[float]` | Vetor semântico gerado da descrição |

### Campos derivados (gerados automaticamente)

| Campo              | Tipo    | Origem |
|--------------------|---------|--------|
| `hora`             | int     | Derivado de `data_hora.hour` (0–23) |
| `dia_semana`       | int     | Derivado de `data_hora.weekday()` (0=seg, 6=dom) |
| `sentimento_score` | float   | Análise de sentimento da descrição |

### Escala das dimensões

- Internamente armazenadas como `float` entre `0.0` e `1.0`
- No formulário frontend: exibidas e coletadas na escala `0–10`
- Conversão: `valor_interno = valor_formulario / 10`

### Default para eventos existentes

Quando as dimensões `sensibilidade`, `serenidade` e `interesse` foram adicionadas ao sistema, todos os eventos já existentes receberam o valor `0.5` (equivalente a 5 na escala 0–10).

---

## 3. Score de bem-estar percebido

O sistema calcula um score composto de bem-estar para cada evento, usado como base em todos os insights comportamentais:

```
bem_estar = média(humor, energia, serenidade, interesse, sensibilidade, 1 - estresse)
```

- Dimensões positivas (humor, energia, serenidade, interesse, sensibilidade): contribuem diretamente
- Estresse: contribui invertido (`1 - estresse`), pois alto estresse reduz bem-estar
- Resultado normalizado entre `0.0` e `1.0`

---

## 4. Presets de entrada rápida

Presets são atalhos de preenchimento. Ao selecionar um preset, os campos de dimensão são preenchidos automaticamente com valores predefinidos.

**Presets disponíveis:** cansada, estressada, ansiosa, tranquila, animada, feliz, triste, irritada, focada, confusa, motivada, entediada, sobrecarregada, empolgada, realizada, grata.

- Cada preset define valores para `energia`, `humor` e `estresse`; as demais dimensões ficam com `0.5`
- O usuário pode sobrescrever qualquer valor antes de salvar

---

## 5. Relações entre eventos — `RelacaoEvento`

Relações representam arestas no grafo de eventos. Cada relação liga dois eventos e tem:

| Campo           | Tipo  | Descrição |
|-----------------|-------|-----------|
| `intensidade`   | float | Força da relação (0.0–1.0), soma das evidências |
| `confiabilidade`| float | 1.0 = criada manualmente; menor = criada automaticamente |
| `motivo`        | texto | Explicação legível do porquê da relação |

### Tipos de relação

- **Manual** (`confiabilidade = 1.0`): criada explicitamente pelo usuário
- **Automática** (`confiabilidade < 1.0`): gerada pelo sistema com base em heurísticas de similaridade

Relações manuais nunca são removidas pelo sistema. Relações automáticas são recriadas a cada save de evento.

---

## 6. Similaridade automática entre eventos

Quando um evento é criado ou atualizado, o sistema recalcula automaticamente as relações automáticas daquele evento com os demais eventos dos últimos **90 dias**.

A similaridade é composta por até quatro fontes de evidência independentes. A intensidade total é a soma das parcelas.

### Fontes de evidência

#### 6.1 Tags em comum
| Condição | Intensidade | Confiabilidade |
|----------|-------------|----------------|
| 1 tag igual | 0.12 | 0.80 |
| 2 tags iguais | 0.18 | 0.85 |
| 3 tags iguais | 0.24 | 0.90 |
| 4+ tags iguais | 0.30 (máx) | 0.95 (máx) |

Motivo gerado: `"tag em comum: trabalho"` / `"tags em comum: trabalho, pressão"`

#### 6.2 Título igual ou muito parecido
| Condição | Intensidade | Confiabilidade |
|----------|-------------|----------------|
| Títulos idênticos (após normalização) | 0.22 | 0.95 |
| SequenceMatcher ≥ 0.88 | 0.18 | 0.88 |

**Regra importante:** embedding **não** é usado para comparar títulos. O modelo confunde domínio semântico com similaridade real (ex: "pilates" e "sono" têm embedding próximo, o que geraria pares sem sentido).

#### 6.3 Dimensões iguais
Compara as 6 dimensões obrigatórias (`humor`, `energia`, `estresse`, `sensibilidade`, `serenidade`, `interesse`) mais as `dimensoes_extras` em comum. Dois valores são considerados iguais se `|a - b| ≤ 0.05` (TOLERANCIA_DIMENSAO).

| Dimensões iguais | Intensidade |
|------------------|-------------|
| 4 | 0.18 |
| 5 | 0.23 |
| 6+ | 0.28 (máx) |

#### 6.4 Similaridade de descrição
| Condição | Intensidade | Confiabilidade |
|----------|-------------|----------------|
| `sim_texto ≥ 0.95` | 0.30 | 0.95 |
| `sim_texto ≥ 0.60` | 0.24 | 0.88 |
| `sim_embedding ≥ 0.76` | 0.22 | 0.82 |
| `sim_embedding ≥ 0.67` e `sim_texto ≥ 0.35` | 0.16 | 0.74 |

O motivo sempre inclui palavras significativas em comum (ex: `"descrições semanticamente próximas (palavras em comum: ansiedade, reunião)"`).

### Limiar de criação

Só gera relação se `intensidade_total ≥ 0.10`. Não há limite máximo de relações por evento.

### Reconciliação

A cada save de evento, o sistema:
1. Calcula as relações desejadas para aquele evento
2. Remove as relações automáticas que não passam mais no limiar
3. Cria ou atualiza as que passam

---

## 7. Embeddings semânticos

Eventos com descrição preenchida recebem um vetor semântico (embedding) gerado pelo modelo `paraphrase-multilingual-MiniLM-L12-v2`.

- O embedding é gerado automaticamente ao criar/editar um evento se a descrição foi alterada
- Usado para calcular similaridade semântica entre descrições
- Armazenado como JSON `[float]` no campo `embedding`

### Ordem de carregamento do modelo
1. Variável de ambiente `EMBEDDING_MODEL_DIR` (se apontar para diretório existente)
2. `models/paraphrase-multilingual-MiniLM-L12-v2/` dentro do projeto
3. Download remoto (só se `EMBEDDING_ALLOW_REMOTE_DOWNLOAD=1`)

---

## 8. Insights comportamentais

Gerados a partir dos eventos dos últimos N dias (padrão: 60). São baseados no score de bem-estar percebido e classificados por relevância. Retornam no máximo 5 insights, selecionados pelos de maior relevância.

### Tipos de insight

| Tipo | Descrição | Mín. eventos |
|------|-----------|--------------|
| `alerta_estado_persistente` | Últimos 3+ de 4 registros com bem-estar < 0.4 | 3 |
| `tendencia_recente` | Compara última semana com a anterior; inclui qual dimensão mais variou | 2+2 |
| `estado_nivel_baixo/alto` | Estado que co-ocorre com bem-estar percebido baixo ou alto | 2 ocorrências |
| `coocorrencia_negativa/positiva` | Estado que aparece em dias com bem-estar percebido mais baixo/alto | 2 dias |
| `densidade_relacional_baixa/alta` | Proporção de eventos conectados no grafo (< 45% ou > 70%) | 4 |
| `predominio_relacoes_automaticas/manuais` | Se ≥ 65% das relações são automáticas ou manuais | 3 relações |
| `associacao_dominante` | Relação com score de evidência mais alto do mapa | — |
| `padrao_horario` | Período do dia com melhor e pior bem-estar percebido | 2+ períodos |
| `padrao_dia_semana` | Dias com melhor e pior bem-estar percebido | 2+ dias |
| `ciclo_comportamental` | Evento que reaparece em intervalos regulares | 2 ocorrências |

### Insights do grafo de relações (separados)

Retornados por endpoint próprio (`/insights/relacoes-insights`):

| Tipo | Descrição |
|------|-----------|
| `hub_emocional` | Evento com mais relações fortes — ponto central do grafo |
| `evolucao_estado` | Evento registrado várias vezes com tendência de melhora ou piora |
| `cluster_emocional` | Grupo de 3+ estados que se relacionam entre si |

---

## 9. Análise de viés de percepção (Perception Bias)

Analisa **como** o usuário registra, não o que registra.

### Viés de valência
Classifica cada evento como `negativo` (humor < 0.35), `positivo` (humor > 0.65) ou `neutro`.
- Se ≥ 65% negativos → insight de viés negativo
- Se ≥ 65% positivos → insight de viés positivo

### Viés de registro
- Tags mais frequentes (top 5)
- Contextos mais frequentes (top 5)
- Aviso se uma tag aparece em ≥ 50% dos registros

### Viés de intensidade
Detecta a proporção de registros com estados extremos:
- Estresse ≥ 0.75
- Humor ≤ 0.25 ou ≥ 0.85
- Energia ≤ 0.25 ou ≥ 0.85
- Serenidade ≤ 0.25
- Interesse ≤ 0.25
- Sensibilidade ≥ 0.85

Calcula também a média de todas as 6 dimensões no período.

---

## 10. Correlações entre dimensões

Calcula correlações de Pearson entre todas as dimensões (as 6 obrigatórias + dimensões extras) usando os eventos do período.

- Mínimo 5 eventos para executar
- Mínimo 3 pontos por par de dimensões
- Só retorna correlações com `|r| ≥ 0.30`
- Intensidade: `"forte"` se `|r| ≥ 0.70`, `"moderada"` caso contrário
- Retorna no máximo 10 correlações ordenadas por `|r|` decrescente

---

## 11. Padrões detectados (`/insights/padroes`)

Análises complementares sobre o período:

- **Frequência por dia da semana**: qual dia tem mais e menos registros
- **Horário de registro**: período do dia com concentração ≥ 35% dos registros
- **Tema recorrente**: tag ou termo de descrição presente em ≥ 20% dos registros
- **Relação dominante**: par de eventos com maior score de evidência
- **Tendência por dimensão**: se `|variação| ≥ 0.10` entre primeira e segunda metade do período (energia, humor, estresse)
- **Energia/humor baixos**: se média ≤ 0.35 no período
- **Estresse alto**: se média ≥ 0.70 no período

---

## 12. Recomendações (`/insights/recomendacoes`)

Baseadas nos últimos 14 dias:

| Condição | Categoria | Prioridade |
|----------|-----------|------------|
| Energia percebida média < 0.35 | energia | alta |
| Humor percebido médio < 0.35 | humor | alta |
| Estresse percebido médio > 0.70 | estresse | alta |
| Registros em < 5 dos últimos 14 dias | habito | baixa |
| Sem alertas | geral | baixa |

---

## 13. Dashboard e streak

### Resumo do período
Calcula médias de todas as 6 dimensões para o período selecionado (14, 30, 60 ou 90 dias).

### Estado de hoje
Média de todas as 6 dimensões dos eventos registrados hoje.

### Streak de registros
- **Streak atual**: dias consecutivos com ao menos um registro (a partir de hoje ou ontem)
- **Streak máximo**: maior sequência histórica de dias consecutivos

---

## 14. Grafo de eventos

Visualização da rede de eventos e relações.

### Coloração dos nós
- Humor percebido ≥ 0.70 → verde claro (`#c8f0d4`)
- Humor percebido ≥ 0.40 → azul claro (`#b8d4f0`)
- Humor percebido < 0.40 → rosa (`#f0b8d4`)

### Tamanho dos nós
Proporcional ao número de relações: `max(10, min(30, 10 + relacoes * 4))`

### Modos
- **Global**: todos os eventos do período (com filtros de data)
- **Local**: subgrafo a partir de um evento central com profundidade configurável (1–4)

### Tooltip de cada nó
Exibe as 6 dimensões: E (energia), H (humor), St (estresse), Sb (sensibilidade), Sr (serenidade), In (interesse)

---

## 15. Similaridade semântica entre eventos

Endpoint `/insights/similaridade/{evento_id}` retorna os eventos semanticamente mais próximos usando similaridade de cosseno entre embeddings.

- Requer que o evento e os candidatos tenham embedding gerado
- Retorna os top-N mais similares (padrão: 5, máximo: 20)

---

## 16. Regras de integridade

- O label do evento é sempre armazenado em **minúsculas**
- `data_hora` é obrigatório; se não informado, usa `datetime.utcnow()`
- Ao excluir um evento, todas as suas relações (origem e destino) são removidas em cascata
- Uma relação não pode ligar um evento a ele mesmo
- Não podem existir duas relações com o mesmo par `(origem_id, destino_id)` na mesma direção

---

## 17. Scripts de manutenção

| Script | Finalidade |
|--------|-----------|
| `scripts/rebuild_auto_relations.py` | Reconstrói todas as relações automáticas com as heurísticas atuais. Preserva manuais. Idempotente. |
| `scripts/backfill_embeddings.py` | Gera embeddings para eventos que ainda não têm. |
| `scripts/download_embedding_model.py` | Baixa o modelo de embedding localmente. |
