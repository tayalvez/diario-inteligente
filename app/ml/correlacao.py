"""Módulo de correlação entre dimensões de eventos."""
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session


def calcular_correlacoes_dimensoes(db: Session, data_inicio: datetime) -> Dict[str, Any]:
    """Correlações de Pearson entre energia, humor, estresse e dimensões extras."""
    try:
        import pandas as pd
        import numpy as np
        from app.models.database import Evento
        import json

        eventos = db.query(Evento).filter(Evento.data_hora >= data_inicio).all()

        if not eventos:
            return {"correlacoes": [], "mensagem": "Nenhum dado encontrado.", "total_eventos": 0}

        registros = []
        for e in eventos:
            row = {
                "energia": e.energia,
                "humor": e.humor,
                "estresse": e.estresse,
                "sensibilidade": e.sensibilidade,
                "serenidade": e.serenidade,
                "interesse": e.interesse,
            }
            if e.dimensoes_extras_json:
                try:
                    extras = json.loads(e.dimensoes_extras_json)
                    if isinstance(extras, dict):
                        row.update(extras)
                except Exception:
                    pass
            registros.append(row)

        if len(registros) < 5:
            return {
                "correlacoes": [],
                "mensagem": "São necessários pelo menos 5 eventos.",
                "total_eventos": len(registros),
            }

        df = pd.DataFrame(registros)
        df = df.dropna(axis=1, how="all")

        if df.shape[1] < 2:
            return {"correlacoes": [], "mensagem": "São necessárias pelo menos 2 dimensões."}

        correlacoes_encontradas = []
        cols = list(df.columns)

        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                a = df[cols[i]].dropna()
                b = df[cols[j]].dropna()
                idx = a.index.intersection(b.index)
                if len(idx) < 3:
                    continue
                a, b = a.loc[idx], b.loc[idx]
                if a.std() == 0 or b.std() == 0:
                    continue

                r = float(np.corrcoef(a, b)[0, 1])
                if abs(r) < 0.3:
                    continue

                intensidade = "forte" if abs(r) >= 0.7 else "moderada"
                direcao = "positiva" if r > 0 else "negativa"
                interpretacao = (
                    f"Nos seus registros, quando '{cols[i]}' aparece alto, '{cols[j]}' tende a aparecer também elevado"
                    if r > 0 else
                    f"Nos seus registros, quando '{cols[i]}' aparece alto, '{cols[j]}' tende a aparecer mais baixo"
                )

                correlacoes_encontradas.append({
                    "dimensao_a": cols[i],
                    "dimensao_b": cols[j],
                    "coeficiente": round(r, 3),
                    "intensidade": intensidade,
                    "direcao": direcao,
                    "interpretacao": interpretacao,
                    "total_pontos": len(idx),
                })

        correlacoes_encontradas.sort(key=lambda x: abs(x["coeficiente"]), reverse=True)

        return {
            "correlacoes": correlacoes_encontradas[:10],
            "total_eventos": len(registros),
            "mensagem": f"Análise baseada em {len(registros)} registros. Correlações refletem padrões percebidos, não causalidade real.",
        }

    except ImportError:
        return {"erro": "pandas/numpy não disponíveis", "correlacoes": []}
    except Exception as e:
        return {"erro": str(e), "correlacoes": []}
