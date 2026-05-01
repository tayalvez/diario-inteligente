# Guia de Boas Práticas de Desenvolvimento de Software

> Referência oficial de desenvolvimento para o projeto. Serve como base para desenvolvedores e agentes automatizados.

---

## Sumário

1. [Introdução](#introdução)
2. [Clean Code](#clean-code)
3. [Princípios SOLID](#princípios-solid)
4. [Arquitetura Limpa](#arquitetura-limpa)
5. [Padrões e Diretrizes de Código](#padrões-e-diretrizes-de-código)
6. [Uso do Português no Código](#uso-do-português-no-código)
7. [Exemplos Práticos](#exemplos-práticos)
8. [Conclusão](#conclusão)

---

## Introdução

### Objetivo

Este guia estabelece os padrões de desenvolvimento adotados neste projeto. Ele centraliza decisões sobre nomenclatura, organização, design e arquitetura, reduzindo ambiguidade e tornando o código uma linguagem compartilhada entre todos os colaboradores — humanos ou automatizados.

### Por que código limpo e arquitetura bem definida importam?

Código é lido muito mais do que é escrito. A maior parte do tempo de um desenvolvedor é gasta entendendo código existente, não criando código novo. Por isso:

- **Manutenção**: código claro reduz o tempo para localizar e corrigir problemas.
- **Escalabilidade**: uma arquitetura bem definida permite crescer sem reescrever tudo.
- **Colaboração**: convenções compartilhadas eliminam discussões desnecessárias e tornam revisões de código mais produtivas.
- **Confiabilidade**: código com responsabilidades bem delimitadas é mais fácil de testar e menos propenso a regressões.

> "Qualquer tolo pode escrever código que um computador entende. Bons programadores escrevem código que humanos entendem." — Martin Fowler

---

## Clean Code

### O que é código limpo?

Código limpo é aquele que **comunica sua intenção claramente**, sem exigir que o leitor decifre o que foi escrito. Ele é simples, direto e previsível. Robert C. Martin define código limpo como código que parece ter sido escrito por alguém que se importa.

---

### Nomes significativos

O nome de uma variável, função ou classe deve responder três perguntas: **por que existe**, **o que faz** e **como é usado**. Se o nome exige um comentário para ser compreendido, ele não é bom o suficiente.

**Ruim:**
```python
d = 0  # dias desde a última modificação
def calc(x, y):
    return x * y * 0.1
```

**Limpo:**
```python
dias_desde_ultima_modificacao = 0

def calcular_desconto(preco, quantidade):
    return preco * quantidade * 0.1
```

Diretrizes:
- Use nomes pronunciáveis e pesquisáveis.
- Evite abreviações que não sejam universais (`qtd` pode ser aceitável, `q` não).
- Classes devem ter nomes substantivos (`Evento`, `RelacaoEvento`).
- Funções devem ter nomes verbais (`calcular_similaridade`, `gerar_embedding`).
- Booleanos devem expressar uma condição (`esta_ativo`, `tem_descricao`).

---

### Funções pequenas e com responsabilidade única

Uma função deve fazer **uma coisa só**, fazê-la bem e não fazer mais nada. Se você precisa de "e" para descrever o que uma função faz, ela provavelmente faz coisas demais.

**Ruim:**
```python
def processar_evento(evento):
    # valida
    if not evento.get("nome"):
        raise ValueError("nome obrigatório")
    # salva no banco
    db.add(evento)
    db.commit()
    # envia notificação
    enviar_email(evento["usuario"], "Evento criado")
```

**Limpo:**
```python
def validar_evento(evento):
    if not evento.get("nome"):
        raise ValueError("nome obrigatório")

def salvar_evento(db, evento):
    db.add(evento)
    db.commit()

def notificar_criacao(evento):
    enviar_email(evento["usuario"], "Evento criado")
```

Limite o tamanho de funções. Se uma função não cabe na tela sem rolar, ela provavelmente faz coisas demais.

---

### Evitar comentários desnecessários

Comentários mentem. Código muda; comentários frequentemente não acompanham. O objetivo é escrever código que **não precise de comentários** para ser compreendido.

**Ruim:**
```python
# Verifica se o usuário está ativo
if u.s == 1:
    ...
```

**Limpo:**
```python
if usuario.esta_ativo:
    ...
```

Quando comentários são válidos:
- Explicar **por que** uma decisão foi tomada (não o que o código faz).
- Documentar workarounds para bugs externos ou restrições não óbvias.
- Avisos de consequências importantes.

```python
# O modelo de embedding ignora textos com menos de 3 tokens;
# por isso verificamos o tamanho antes de chamar o encode.
if len(texto.split()) >= 3:
    vetor = modelo.encode(texto)
```

---

### Tratamento de erros

Erros fazem parte do fluxo normal de um sistema. Tratá-los bem é parte do código limpo.

- Prefira exceções a códigos de retorno.
- Não capture exceções genéricas sem motivo.
- Não silencia erros com `except: pass`.
- Falhe cedo e de forma clara.

**Ruim:**
```python
def obter_embedding(texto):
    try:
        return modelo.encode(texto)
    except:
        return None
```

**Limpo:**
```python
def obter_embedding(texto: str) -> list[float] | None:
    if not texto or not texto.strip():
        return None
    try:
        return modelo.encode(texto.strip()).tolist()
    except Exception as e:
        logger.error(f"[embedding] falha ao gerar vetor: {e}")
        return None
```

---

### Legibilidade e simplicidade

- Prefira código explícito a código inteligente.
- Evite aninhamentos profundos — use retorno antecipado (*early return*).
- Não otimize prematuramente.

**Ruim:**
```python
def processar(itens):
    resultado = []
    for item in itens:
        if item.ativo:
            if item.valor > 0:
                resultado.append(item.valor * 1.1)
    return resultado
```

**Limpo:**
```python
def processar(itens):
    return [
        item.valor * 1.1
        for item in itens
        if item.ativo and item.valor > 0
    ]
```

---

## Princípios SOLID

SOLID é um conjunto de cinco princípios para design de software orientado a objetos que tornam sistemas mais compreensíveis, flexíveis e manuteníveis.

---

### SRP — Princípio da Responsabilidade Única

> *"Uma classe deve ter um, e somente um, motivo para mudar."*

**Problema que resolve:** classes com múltiplas responsabilidades mudam por razões diferentes, tornando o código frágil e difícil de testar.

**Ruim:**
```python
class Relatorio:
    def gerar(self): ...
    def formatar_pdf(self): ...
    def enviar_por_email(self): ...
```

**Limpo:**
```python
class GeradorRelatorio:
    def gerar(self): ...

class FormataRelatorio:
    def para_pdf(self, relatorio): ...

class EnviadorRelatorio:
    def por_email(self, relatorio, destinatario): ...
```

---

### OCP — Princípio Aberto/Fechado

> *"Entidades de software devem ser abertas para extensão, mas fechadas para modificação."*

**Problema que resolve:** modificar código existente para adicionar comportamentos introduz risco de regressão.

**Ruim:**
```python
def calcular_area(forma):
    if forma.tipo == "circulo":
        return 3.14 * forma.raio ** 2
    elif forma.tipo == "retangulo":
        return forma.largura * forma.altura
```

**Limpo:**
```python
class Circulo:
    def area(self): return 3.14 * self.raio ** 2

class Retangulo:
    def area(self): return self.largura * self.altura

def calcular_area(forma):
    return forma.area()
```

Adicionar um triângulo não requer modificar `calcular_area` — apenas criar uma nova classe.

---

### LSP — Princípio da Substituição de Liskov

> *"Subtipos devem ser substituíveis por seus tipos base sem alterar o comportamento correto do programa."*

**Problema que resolve:** herança mal usada cria contratos quebrados — a subclasse não se comporta como prometido pela classe pai.

**Ruim:**
```python
class Ave:
    def voar(self): ...

class Pinguim(Ave):
    def voar(self):
        raise NotImplementedError("Pinguins não voam")
```

**Limpo:**
```python
class Ave:
    def mover(self): ...

class AveVoadora(Ave):
    def voar(self): ...

class Pinguim(Ave):
    def nadar(self): ...
```

---

### ISP — Princípio da Segregação de Interfaces

> *"Clientes não devem ser forçados a depender de interfaces que não utilizam."*

**Problema que resolve:** interfaces grandes obrigam implementações desnecessárias e criam acoplamento artificial.

**Ruim:**
```python
class Repositorio:
    def salvar(self): ...
    def buscar(self): ...
    def exportar_csv(self): ...
    def enviar_relatorio(self): ...
```

**Limpo:**
```python
class RepositorioDados:
    def salvar(self): ...
    def buscar(self): ...

class ExportadorDados:
    def exportar_csv(self): ...

class EnviadorRelatorio:
    def enviar(self): ...
```

---

### DIP — Princípio da Inversão de Dependência

> *"Módulos de alto nível não devem depender de módulos de baixo nível. Ambos devem depender de abstrações."*

**Problema que resolve:** acoplar lógica de negócio diretamente a implementações concretas (banco, e-mail, etc.) torna o sistema rígido e difícil de testar.

**Ruim:**
```python
class ServicoEvento:
    def __init__(self):
        self.db = SQLiteDatabase()  # acoplado à implementação
```

**Limpo:**
```python
class ServicoEvento:
    def __init__(self, repositorio: RepositorioEvento):
        self.repositorio = repositorio  # depende da abstração
```

Com isso, o repositório pode ser trocado por um mock em testes sem alterar `ServicoEvento`.

---

## Arquitetura Limpa

### Conceito geral

A Arquitetura Limpa, proposta por Robert C. Martin, organiza o sistema em **camadas concêntricas** onde as dependências sempre apontam para dentro — das camadas externas (frameworks, UI, banco) em direção ao núcleo (regras de negócio).

O objetivo é que as **regras de negócio sejam completamente independentes** de tecnologia. O banco de dados pode ser trocado. O framework web pode mudar. A UI pode ser substituída. O núcleo permanece intacto.

---

### Separação de camadas

```
┌──────────────────────────────────────┐
│         Frameworks & Drivers         │  ← FastAPI, SQLite, Angular
│  ┌────────────────────────────────┐  │
│  │     Interface Adapters         │  │  ← APIs, repositórios, schemas
│  │  ┌──────────────────────────┐  │  │
│  │  │     Casos de Uso         │  │  │  ← lógica de aplicação
│  │  │  ┌────────────────────┐  │  │  │
│  │  │  │     Entidades      │  │  │  │  ← regras de negócio puras
│  │  │  └────────────────────┘  │  │  │
│  │  └──────────────────────────┘  │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

#### Entidades
Contêm as **regras de negócio fundamentais** — as que existiriam independentemente de qualquer sistema. São os modelos centrais do domínio.

```python
# Entidade pura — não sabe nada de banco, HTTP ou framework
class Evento:
    def __init__(self, nome, data_hora, energia, humor, estresse):
        self.nome = nome
        self.data_hora = data_hora
        self.energia = energia
        self.humor = humor
        self.estresse = estresse

    def esta_completo(self) -> bool:
        return all([self.nome, self.data_hora])
```

#### Casos de Uso
Contêm a **lógica de aplicação** — orquestram entidades para atingir um objetivo específico do sistema. Não dependem de frameworks.

```python
class CriarEvento:
    def __init__(self, repositorio: RepositorioEvento):
        self.repositorio = repositorio

    def executar(self, dados: dict) -> Evento:
        evento = Evento(**dados)
        if not evento.esta_completo():
            raise ValueError("Dados insuficientes para criar evento")
        return self.repositorio.salvar(evento)
```

#### Interface Adapters (Adaptadores)
Traduzem dados entre o formato dos casos de uso e o formato do mundo externo (banco, HTTP, CLI).

```python
# Adaptador para a API HTTP (FastAPI)
@router.post("/eventos")
def criar_evento(dados: EventoSchema, db: Session = Depends(get_db)):
    repositorio = RepositorioEventoSQLite(db)
    caso_de_uso = CriarEvento(repositorio)
    return caso_de_uso.executar(dados.dict())
```

#### Frameworks & Drivers
A camada mais externa — FastAPI, SQLAlchemy, Angular, SQLite. Nenhuma regra de negócio deve viver aqui.

---

### Regra de dependência

**As dependências só apontam para dentro.** Uma camada interna nunca conhece nada sobre uma camada externa.

- Entidades não importam casos de uso.
- Casos de uso não importam adaptadores.
- Adaptadores não importam frameworks diretamente — usam interfaces.

---

### Independência de frameworks, UI e banco de dados

- O framework é um detalhe. A lógica de negócio não deve usar decoradores, objetos ou convenções específicas do framework.
- O banco de dados é um detalhe. Use repositórios como abstração — trocar SQLite por PostgreSQL não deve exigir mudanças nos casos de uso.
- A UI é um detalhe. A lógica de negócio não sabe se é uma API REST, CLI ou interface gráfica.

---

### Testabilidade

Uma arquitetura limpa é naturalmente testável porque as dependências externas são abstraídas. Casos de uso podem ser testados sem banco de dados real, sem servidor HTTP e sem a UI.

```python
def test_criar_evento_valido():
    repositorio = RepositorioEventoFake()
    caso_de_uso = CriarEvento(repositorio)
    evento = caso_de_uso.executar({
        "nome": "ansiedade",
        "data_hora": datetime.now(),
        "energia": 0.5,
        "humor": 0.4,
        "estresse": 0.7,
    })
    assert evento.nome == "ansiedade"
    assert repositorio.foi_salvo(evento)
```

---

### Exemplo de organização de pastas

```
projeto/
├── app/
│   ├── models/          ← entidades e acesso ao banco (ORM)
│   ├── schemas/         ← contratos de entrada/saída (Pydantic)
│   ├── api/             ← adaptadores HTTP (rotas FastAPI)
│   ├── services/        ← casos de uso / lógica de aplicação
│   └── ml/              ← módulos de aprendizado de máquina
├── scripts/             ← utilitários e scripts de manutenção
├── tests/               ← testes automatizados
└── frontend/            ← interface (Angular)
```

---

## Padrões e Diretrizes de Código

### Convenções de nomenclatura

| Elemento | Convenção | Exemplo |
|---|---|---|
| Variável | snake_case | `dias_desde_criacao` |
| Função | snake_case, verbo | `calcular_similaridade` |
| Classe | PascalCase, substantivo | `RelacaoEvento` |
| Constante | UPPER_SNAKE_CASE | `LIMIAR_SIMILARIDADE` |
| Arquivo | snake_case | `rebuild_auto_relations.py` |
| Módulo | snake_case | `app/ml/similaridade.py` |

---

### Organização de arquivos

- Um arquivo por responsabilidade principal.
- Arquivos de teste espelham a estrutura do código: `app/ml/similaridade.py` → `tests/test_similaridade.py`.
- Scripts de manutenção em `scripts/`, isolados da aplicação.

---

### Boas práticas de testes

- Cada teste verifica **uma única coisa**.
- Nomes de testes descrevem o comportamento esperado: `test_descricao_contida_gera_relacao`.
- Use mocks apenas para dependências externas reais (HTTP, e-mail). Prefira implementações falsas (*fakes*) para repositórios.
- Testes devem ser rápidos, independentes e repetíveis.
- A ordem de execução dos testes não deve importar.

```python
# Bom: nome descreve o comportamento
def test_eventos_sem_descricao_nao_geram_embedding():
    ...

# Ruim: nome não comunica intenção
def test_1():
    ...
```

---

### Evitar acoplamento forte

- Prefira injeção de dependência a instanciação direta.
- Evite variáveis globais mutáveis.
- Não acesse o banco de dados diretamente de dentro de rotas — use repositórios ou serviços.
- Não coloque lógica de negócio em schemas ou modelos ORM.

---

## Uso do Português no Código

### Preferência pelo português

Este projeto adota **português como idioma padrão** para nomes de variáveis, funções, classes, arquivos e comentários. O código reflete o domínio do problema — que é em português — tornando a leitura mais natural e a comunicação mais direta.

### Justificativa

- **Clareza para o time**: nomes no idioma nativo eliminam a tradução mental constante.
- **Coerência com o domínio**: termos como `evento`, `relacao`, `humor`, `estresse` expressam o modelo de negócio diretamente.
- **Redução de ambiguidade**: traduzir conceitos de domínio para inglês frequentemente gera nomes vagos ou incorretos.

### Exemplos comparativos

| Inglês | Português | Por que o português é melhor aqui |
|---|---|---|
| `event` | `evento` | termo do domínio |
| `relationship` | `relacao` | mais específico no contexto |
| `mood` | `humor` | traduz o conceito com precisão |
| `stress_level` | `estresse` | direto ao ponto |
| `confidence` | `confiabilidade` | reflete o significado no domínio |

### Exceções — quando usar inglês

Use inglês quando o termo fizer parte do **vocabulário padrão da linguagem ou ecossistema**:

```python
# Inglês: convenção do Python e do SQLAlchemy
class Evento(Base):
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True)

# Inglês: convenção do FastAPI
@router.get("/eventos")
def listar_eventos():
    ...

# Inglês: métodos herdados de frameworks
def model_post_init(self): ...
def setUp(self): ...
```

Outras exceções:
- Nomes de bibliotecas e dependências externas.
- Termos técnicos sem tradução estabelecida (`embedding`, `token`, `score`, `batch`).
- Código destinado a contribuição em projetos open source internacionais.

### Regra prática

> Se o termo existe em português no vocabulário do domínio, use português. Se é um termo técnico universal sem tradução natural, mantenha em inglês.

---

## Exemplos Práticos

### Código ruim vs código limpo

**Ruim:**
```python
def f(e, db):
    if e["n"] and e["d"] and e["h"] and e["hu"] and e["es"]:
        x = db.query(M).filter(M.id == e["id"]).first()
        if x:
            x.n = e["n"]
            db.commit()
            return True
    return False
```

**Limpo:**
```python
def atualizar_evento(dados: dict, db: Session) -> Evento:
    _validar_campos_obrigatorios(dados)
    evento = _buscar_evento_ou_falhar(dados["id"], db)
    evento.nome = dados["nome"]
    db.commit()
    return evento
```

---

### Violação vs aplicação de SOLID

**Violação do SRP:**
```python
class EventoService:
    def salvar(self, evento): ...
    def calcular_similaridade(self, a, b): ...
    def gerar_relatorio(self): ...
    def enviar_notificacao(self): ...
```

**Aplicação do SRP:**
```python
class RepositorioEvento:
    def salvar(self, evento): ...

class SimilaridadeService:
    def calcular(self, a, b): ...

class RelatorioService:
    def gerar(self): ...
```

---

### Estrutura antes/depois da Arquitetura Limpa

**Antes — lógica de negócio acoplada à rota:**
```python
@router.post("/eventos")
def criar_evento(dados: dict, db: Session = Depends(get_db)):
    if not dados.get("nome"):
        raise HTTPException(400, "nome obrigatório")
    evento = Evento(**dados)
    db.add(evento)
    db.commit()
    # gera embedding direto na rota
    vetor = modelo.encode(dados.get("descricao", ""))
    evento.embedding = json.dumps(vetor.tolist())
    db.commit()
    return evento
```

**Depois — responsabilidades separadas:**
```python
# rota: só traduz HTTP para caso de uso
@router.post("/eventos")
def criar_evento(dados: EventoSchema, db: Session = Depends(get_db)):
    repositorio = RepositorioEventoSQLite(db)
    return CriarEvento(repositorio).executar(dados.dict())

# caso de uso: orquestra a lógica
class CriarEvento:
    def executar(self, dados: dict) -> Evento:
        validar_evento(dados)
        evento = self.repositorio.salvar(Evento(**dados))
        self.repositorio.atualizar_embedding(evento)
        return evento
```

---

## Conclusão

Código limpo, princípios sólidos e arquitetura bem definida não são luxos — são a base para que um projeto cresça sem se tornar um fardo. Cada decisão de design é um investimento: feita com cuidado, reduz o custo de todas as mudanças futuras.

Alguns pontos para carregar:

- **Consistência importa mais que perfeição**: um padrão aplicado de forma consistente vale mais do que o padrão ideal aplicado em metade do código.
- **Código é comunicação**: você escreve para o próximo desenvolvedor que vai ler, não para o computador que vai executar.
- **Evolução contínua**: refatorar é parte do trabalho, não um sinal de falha. Um código que nunca melhora está envelhecendo.
- **Simples é difícil**: a solução mais simples que resolve o problema é quase sempre a melhor — e é a mais difícil de encontrar.

> "O único jeito de ir rápido é ir bem." — Robert C. Martin
