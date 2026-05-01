import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ml.similaridade import gerar_relacoes_similaridade
from app.models.database import Evento, RelacaoEvento, SessionLocal


def _pair_key(origem_id: int, destino_id: int) -> tuple[int, int]:
    return (min(origem_id, destino_id), max(origem_id, destino_id))


def main() -> None:
    db = SessionLocal()
    criadas = 0
    atualizadas = 0
    removidas = 0

    try:
        eventos = db.query(Evento).order_by(Evento.data_hora.asc(), Evento.id.asc()).all()
        existentes = db.query(RelacaoEvento).all()
        manuais = [r for r in existentes if r.confiabilidade >= 1.0]
        automaticas = [r for r in existentes if r.confiabilidade < 1.0]

        pares_manuais = {_pair_key(r.origem_id, r.destino_id) for r in manuais}
        desejadas = gerar_relacoes_similaridade(eventos, pares_manuais)
        desejadas_por_par = {
            _pair_key(rel["origem_id"], rel["destino_id"]): rel
            for rel in desejadas
        }
        automaticas_por_par = {
            _pair_key(r.origem_id, r.destino_id): r
            for r in automaticas
        }

        # Remove relações automáticas antigas que não sobreviveram à heurística atual.
        for par, rel in automaticas_por_par.items():
            if par not in desejadas_por_par:
                db.delete(rel)
                removidas += 1

        # Atualiza relações automáticas existentes ou cria novas.
        for par, rel_desejada in desejadas_por_par.items():
            existente = automaticas_por_par.get(par)
            if existente:
                existente.origem_id = rel_desejada["origem_id"]
                existente.destino_id = rel_desejada["destino_id"]
                existente.intensidade = rel_desejada["intensidade"]
                existente.confiabilidade = rel_desejada["confiabilidade"]
                existente.motivo = rel_desejada.get("motivo")
                atualizadas += 1
                continue

            db.add(
                RelacaoEvento(
                    origem_id=rel_desejada["origem_id"],
                    destino_id=rel_desejada["destino_id"],
                    intensidade=rel_desejada["intensidade"],
                    confiabilidade=rel_desejada["confiabilidade"],
                    motivo=rel_desejada.get("motivo"),
                )
            )
            criadas += 1

        db.commit()
        print(
            json.dumps(
                {
                    "eventos_analisados": len(eventos),
                    "relacoes_existentes": len(existentes),
                    "relacoes_manuais_preservadas": len(manuais),
                    "relacoes_automaticas_reconciliadas": len(desejadas),
                    "relacoes_criadas": criadas,
                    "relacoes_atualizadas": atualizadas,
                    "relacoes_removidas": removidas,
                },
                ensure_ascii=False,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
