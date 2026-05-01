# Diário de Anotações

Sistema pessoal de captura e análise de anotações internas, com estética cozy e interface estilo caderno.

**Autora do código:** T. Alves

## Conceito central

Uma **Anotação** é o registro de um estado interno em um momento específico, contendo:

- **título** — identificação subjetiva (ex: "cansada", "animada")
- **data** — timestamp do momento
- **dimensões obrigatórias** — energia, humor, estresse (escala 0.0–1.0)
- **dimensões extras** — livres, definidas pelo usuário (ex: foco, disposição)
- **descrição** — contexto livre (opcional)
- **contexto** — pares chave-valor (ex: local, atividade)
- **tags** — palavras-chave manuais
- **relações** — ligações com outras anotações (intensidade + confiabilidade)

## Estrutura mínima

```json
{
  "evento": "cansada",
  "data_hora": "2026-04-18T22:00:00",
  "energia": 0.3,
  "humor": 0.5,
  "estresse": 0.6
}
```

## Estrutura completa

```json
{
  "evento": "estressada",
  "data_hora": "2026-04-18T18:30:00",
  "energia": 0.2,
  "humor": 0.3,
  "estresse": 0.8,
  "descricao": "reunião longa no trabalho",
  "contexto": { "local": "trabalho", "atividade": "reunião" },
  "tags": ["trabalho", "pressão"],
  "dimensoes_extras": { "foco": 0.4 },
  "relacoes": [
    { "evento_id": 12, "intensidade": 0.8, "confiabilidade": 1.0 }
  ]
}
```

## Funcionalidades

- Formulário progressivo: básico → avançado (tags, contexto, dimensões extras, relações)
- Modal estilo caderno com temas visuais escolhíveis
- Relações entre anotações criadas na hora do registro ou posteriormente
- Histórico com gráfico de tendências (humor, energia, estresse)
- Grafo interativo de relações entre anotações
- Análise de padrões comportamentais e correlações entre dimensões
- Recomendações personalizadas baseadas nos dados
- Responsivo — funciona no celular com bottom nav
- Persistência de preferências no localStorage (tema do caderno)

## Temas do caderno

O modal de nova anotação suporta temas visuais de fundo:

| Tema | Descrição |
|------|-----------|
| Padrão | Caderno creme com linhas suaves |
| Urso | Urso e coelho com fundo bege |
| Coelho | Coelhinhos suaves, tom neutro |
| Tech | Azul kawaii com elementos tech |
| Lilás | Fundo lilás com nuvens e personagens |

## Tech Stack

- **Backend**: FastAPI + SQLite + SQLAlchemy
- **Frontend**: Angular 21 + Chart.js + vis.js
- **Fontes**: Caveat (manuscrita) + Nunito (corpo)
- **Ícones**: Phosphor Icons

## Como rodar

### Pré-requisitos
- Python 3.11+
- Node.js 20+

### Setup (primeira vez)

```bash
# Linux/Mac
chmod +x setup.sh && ./setup.sh

# Windows
setup.bat
```

### Iniciar

```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

Acesse em: `http://localhost:4200`

API docs: `http://localhost:8000/docs`

## Embeddings em deploy

Para o app rodar em outros servidores sem depender de internet no runtime, o modelo
de embeddings deve ficar salvo localmente no servidor.

### Estrutura recomendada

```text
diario/
├── models/
│   └── paraphrase-multilingual-MiniLM-L12-v2/
```

### Baixar o modelo uma vez

Em uma máquina com internet, rode:

```bash
venv/bin/python scripts/download_embedding_model.py
```

Isso salva o modelo em `models/paraphrase-multilingual-MiniLM-L12-v2`.

Depois, no servidor de destino, leve essa pasta junto com o deploy.

### Como o backend resolve o modelo

O backend agora carrega o modelo nesta ordem:

1. `EMBEDDING_MODEL_DIR`, se definido
2. `models/paraphrase-multilingual-MiniLM-L12-v2` no projeto
3. download remoto apenas se `EMBEDDING_ALLOW_REMOTE_DOWNLOAD=1`

Exemplo para outro caminho local:

```bash
export EMBEDDING_MODEL_DIR=/opt/diario/models/paraphrase-multilingual-MiniLM-L12-v2
```

Em produção, o ideal é **nao** depender de download remoto.

### Reprocessar eventos antigos

Depois de instalar o modelo localmente, você pode preencher embeddings faltantes e
recriar relações automáticas já com a semântica ativa:

```bash
venv/bin/python scripts/backfill_embeddings.py
venv/bin/python scripts/rebuild_auto_relations.py
```

## Estrutura

```
diario/
├── app/
│   ├── api/
│   │   ├── eventos.py    # CRUD + relações inline + presets + estado agregado
│   │   ├── dashboard.py  # Estatísticas e streak
│   │   ├── insights.py   # Padrões, correlações, recomendações
│   │   └── grafo.py      # Visualização da rede
│   ├── models/database.py   # Evento, RelacaoEvento, InsightGerado
│   ├── schemas/evento.py    # Pydantic schemas
│   └── ml/correlacao.py     # Correlação de Pearson entre dimensões
├── frontend/src/app/
│   ├── components/
│   │   ├── experiencias/  # Tela de anotações (modal caderno + temas)
│   │   ├── dashboard/     # Visão geral com barras de estado
│   │   ├── grafo/         # Rede de relações (vis.js)
│   │   └── insights/      # IA e análises
│   ├── models/types.ts    # Interfaces TypeScript
│   └── services/api.ts    # Client HTTP
├── frontend/src/assets/
│   └── backgrounds/       # Imagens de tema do caderno
└── data/diario.db         # Banco SQLite
```

## Regras de agregação

| Dimensão | Regra   |
|----------|---------|
| energia  | média   |
| humor    | média   |
| estresse | média   |

## Relações entre anotações

| Campo          | Descrição                             |
|----------------|---------------------------------------|
| intensidade    | 0.0–1.0: força da conexão            |
| confiabilidade | 0.0–1.0: 1.0 = manual, menor = auto |

Relações podem ser criadas **na hora do registro** (enviadas inline no payload) ou **ao editar** uma anotação existente.
