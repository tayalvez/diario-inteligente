"""
Serviço de cálculo de impacto emocional.
Analisa título + descrição + contexto do evento e retorna deltas para
humor, energia e estresse, levando em conta categoria, intensidade e recuperação.
"""
from typing import Dict, Tuple

# Impacto base por categoria e valência (humor, energia, estresse)
_IMPACTO_BASE: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "treino":     {"positivo": ( 1.5, -0.5, -1.0), "neutro": ( 0.5, -0.5,  0.0), "negativo": (-0.5, -1.5,  1.0)},
    "sono":       {"positivo": ( 1.5,  2.0, -1.5), "neutro": ( 0.0,  0.5, -0.5), "negativo": (-1.5, -2.0,  2.0)},
    "trabalho":   {"positivo": ( 1.0,  0.0, -0.5), "neutro": ( 0.0, -0.5,  0.5), "negativo": (-1.0, -1.0,  2.0)},
    "social":     {"positivo": ( 1.5,  0.5, -1.0), "neutro": ( 0.5,  0.0,  0.0), "negativo": (-1.5, -0.5,  1.5)},
    "saude":      {"positivo": ( 1.0,  1.0, -1.0), "neutro": ( 0.0,  0.0,  0.5), "negativo": (-1.5, -1.0,  2.0)},
    "meditacao":  {"positivo": ( 1.5,  0.5, -2.0), "neutro": ( 1.0,  0.0, -1.5), "negativo": ( 0.5,  0.0, -0.5)},
    "emocao":     {"positivo": ( 2.0,  0.5, -1.0), "neutro": ( 0.0,  0.0,  0.5), "negativo": (-2.0, -0.5,  2.5)},
    "sentimento": {"positivo": ( 1.5,  0.5, -1.0), "neutro": ( 0.0,  0.0,  0.5), "negativo": (-2.0, -0.5,  2.0)},
    "lazer":      {"positivo": ( 1.5,  1.0, -1.5), "neutro": ( 0.5,  0.5, -0.5), "negativo": (-0.5, -0.5,  0.5)},
    "estudo":     {"positivo": ( 0.5, -0.5,  0.0), "neutro": ( 0.0, -0.5,  0.5), "negativo": (-0.5, -1.0,  1.5)},
    "refeicao":   {"positivo": ( 0.5,  1.0, -0.5), "neutro": ( 0.0,  0.5,  0.0), "negativo": (-0.5, -0.5,  0.5)},
    "pensamento": {"positivo": ( 0.5,  0.0, -0.5), "neutro": ( 0.0,  0.0,  0.0), "negativo": (-0.5,  0.0,  1.0)},
    "percepcao":  {"positivo": ( 0.5,  0.0, -0.5), "neutro": ( 0.0,  0.0,  0.0), "negativo": (-0.5,  0.0,  0.5)},
    "cafe":       {"positivo": ( 0.5,  1.0,  0.0), "neutro": ( 0.0,  0.5,  0.0), "negativo": (-0.5,  0.0,  0.5)},
    "agua":       {"positivo": ( 0.0,  0.5,  0.0), "neutro": ( 0.0,  0.0,  0.0), "negativo": ( 0.0, -0.5,  0.0)},
    "medicacao":  {"positivo": ( 0.5,  0.5, -0.5), "neutro": ( 0.0,  0.0,  0.0), "negativo": (-0.5, -0.5,  1.0)},
    "transporte": {"positivo": ( 0.0,  0.0, -0.5), "neutro": ( 0.0, -0.5,  0.0), "negativo": (-0.5, -0.5,  1.0)},
    "familia":    {"positivo": ( 1.5,  0.5, -1.0), "neutro": ( 0.0,  0.0,  0.0), "negativo": (-1.5, -0.5,  1.5)},
    "outro":      {"positivo": ( 0.5,  0.0, -0.5), "neutro": ( 0.0,  0.0,  0.0), "negativo": (-0.5,  0.0,  0.5)},
}

# Classificação automática de categoria por palavras-chave
_PALAVRAS_CATEGORIA = {
    "trabalho":   ["trabalho", "reunião", "projeto", "chefe", "colega", "empresa", "tarefa", "prazo", "entrega", "escritório", "cliente"],
    "social":     ["amigo", "amiga", "encontro", "conversa", "saída", "festa", "grupo", "família", "namorado", "namorada", "parceiro"],
    "saude":      ["dor", "médico", "hospital", "remédio", "exame", "consulta", "sintoma", "febre", "enjoo", "cansaço físico"],
    "emocao":     ["ansiedade", "medo", "raiva", "alegria", "tristeza", "angústia", "euforia", "frustração", "emoção", "sentimento"],
    "lazer":      ["jogo", "filme", "série", "passeio", "viagem", "hobby", "música", "livro", "descanso", "relaxar"],
    "estudo":     ["estudo", "aula", "curso", "prova", "aprender", "leitura", "pesquisa", "escola", "faculdade"],
    "sono":       ["sono", "dormir", "acordei", "pesadelo", "insônia", "dormiu", "cama", "noite"],
    "treino":     ["treino", "academia", "corrida", "exercício", "musculação", "caminhada", "esporte", "atividade física"],
    "meditacao":  ["meditação", "respiração", "mindfulness", "relaxamento", "ioga", "yoga"],
}


def classificar_categoria(titulo: str, descricao: str, tipo_nome: str) -> str:
    """Determina a categoria emocional do evento."""
    if tipo_nome and tipo_nome in _IMPACTO_BASE:
        return tipo_nome

    texto = f"{titulo} {descricao}".lower()
    for cat, palavras in _PALAVRAS_CATEGORIA.items():
        if any(p in texto for p in palavras):
            return cat
    return "outro"


def calcular_valencia(titulo: str, descricao: str, contexto: str = "") -> str:
    """Determina a valência emocional do texto."""
    from app.ml.nlp import analisar_sentimento
    texto = f"{titulo}. {descricao}. {contexto or ''}".strip()
    resultado = analisar_sentimento(texto)
    return resultado.get("label", "neutro")


def calcular_impacto(
    titulo: str,
    descricao: str,
    tipo_nome: str,
    contexto: str = "",
    intensidade: float = 0.5,
    recuperacao: bool | None = None,
) -> dict:
    """
    Calcula o impacto emocional de um evento.

    Retorna:
        {
          "delta_humor": float,
          "delta_energia": float,
          "delta_estresse": float,
          "valencia": str,         # positiva | neutra | negativa
          "intensidade_label": str, # baixa | média | alta
          "categoria": str,
        }
    """
    categoria = classificar_categoria(titulo, descricao, tipo_nome)
    valencia = calcular_valencia(titulo, descricao, contexto)

    base = _IMPACTO_BASE.get(categoria, _IMPACTO_BASE["outro"])
    dh, de, ds = base.get(valencia, base["neutro"])

    # Multiplicador de intensidade: 0→0.3, 0.5→1.0, 1.0→1.7
    mult_int = 0.3 + (intensidade if intensidade is not None else 0.5) * 1.4

    # Modificador de recuperação
    mult_rec = 1.3 if recuperacao is True else (0.8 if recuperacao is False else 1.0)

    mult = round(mult_int * mult_rec, 3)
    dh = round(dh * mult, 2)
    de = round(de * mult, 2)
    ds = round(ds * mult, 2)

    if intensidade is None or intensidade < 0.35:
        intensidade_label = "baixa"
    elif intensidade < 0.65:
        intensidade_label = "média"
    else:
        intensidade_label = "alta"

    return {
        "delta_humor":    dh,
        "delta_energia":  de,
        "delta_estresse": ds,
        "valencia":       valencia,
        "intensidade_label": intensidade_label,
        "categoria":      categoria,
    }


def recomputar_estado_dia(db, data_alvo) -> None:
    """
    Reconstrói do zero o estado emocional de um dia,
    aplicando os impactos de todos os seus eventos em ordem cronológica.
    """
    from datetime import datetime as _dt
    from app.models.database import EstadoEmocionalDiario, Evento

    inicio = _dt.combine(data_alvo, _dt.min.time())
    fim    = _dt.combine(data_alvo, _dt.max.time())

    eventos_do_dia = (
        db.query(Evento)
        .filter(Evento.timestamp >= inicio, Evento.timestamp <= fim)
        .order_by(Evento.timestamp.asc())
        .all()
    )

    estado = db.query(EstadoEmocionalDiario).filter(
        EstadoEmocionalDiario.data == data_alvo
    ).first()

    if not eventos_do_dia:
        if estado:
            # Sem eventos: volta ao padrão
            estado.humor_atual    = 6.0
            estado.energia_atual  = 6.0
            estado.estresse_atual = 2.0
            estado.transicoes     = "[]"
            estado.atualizado_em  = _dt.utcnow()
        return

    if not estado:
        estado = EstadoEmocionalDiario(
            data=data_alvo, humor_atual=6.0, energia_atual=6.0,
            estresse_atual=2.0, transicoes="[]",
        )
        db.add(estado)
        db.flush()

    # Reset ao padrão e reaplicar todos os eventos do dia
    estado.humor_atual    = 6.0
    estado.energia_atual  = 6.0
    estado.estresse_atual = 2.0
    estado.transicoes     = "[]"

    for ev in eventos_do_dia:
        if ev.impacto_humor is not None:
            imp = {
                "delta_humor":    ev.impacto_humor,
                "delta_energia":  ev.impacto_energia,
                "delta_estresse": ev.impacto_estresse,
                "valencia":       ev.valencia or "neutro",
            }
            aplicar_impacto_ao_estado(estado, imp, ev.id, ev.titulo)

    estado.atualizado_em = _dt.utcnow()


def aplicar_impacto_ao_estado(estado, impacto: dict, evento_id: int, evento_titulo: str) -> None:
    """Aplica os deltas ao estado emocional diário (in-place)."""
    import json
    from datetime import datetime

    estado.humor_atual   = round(max(0.0, min(10.0, estado.humor_atual   + impacto["delta_humor"])),   2)
    estado.energia_atual = round(max(0.0, min(10.0, estado.energia_atual + impacto["delta_energia"])), 2)
    estado.estresse_atual = round(max(0.0, min(10.0, estado.estresse_atual + impacto["delta_estresse"])), 2)

    transicoes = json.loads(estado.transicoes or "[]")
    transicoes.append({
        "evento_id":     evento_id,
        "evento_titulo": evento_titulo,
        "delta_humor":   impacto["delta_humor"],
        "delta_energia": impacto["delta_energia"],
        "delta_estresse":impacto["delta_estresse"],
        "valencia":      impacto["valencia"],
        "timestamp":     datetime.utcnow().isoformat(),
    })
    estado.transicoes = json.dumps(transicoes, ensure_ascii=False)
