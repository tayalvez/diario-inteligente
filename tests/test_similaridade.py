import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.ml.similaridade import calcular_similaridade


def evento_fake(
    evento: str,
    descricao: str,
    *,
    tags=None,
    humor: float = 0.5,
    energia: float = 0.5,
    estresse: float = 0.5,
    sensibilidade: float = 0.5,
    serenidade: float = 0.5,
    interesse: float = 0.5,
    dimensoes_extras=None,
    embedding=None,
):
    return SimpleNamespace(
        id=0,
        evento=evento,
        descricao=descricao,
        tags_json=json.dumps(tags, ensure_ascii=False) if tags is not None else None,
        contexto_json=None,
        dimensoes_extras_json=json.dumps(dimensoes_extras, ensure_ascii=False) if dimensoes_extras is not None else None,
        humor=humor,
        energia=energia,
        estresse=estresse,
        sensibilidade=sensibilidade,
        serenidade=serenidade,
        interesse=interesse,
        embedding=embedding,
    )


class SimilaridadeDescricaoTest(unittest.TestCase):
    def test_descricao_contida_gera_relacao(self):
        a = evento_fake("teste", "acordei ansiosa")
        b = evento_fake(
            "exame periódico",
            "acordei cedo pra fazer exame periódico da consultoria e acordei ansiosa",
        )

        score, confianca, motivo = calcular_similaridade(a, b)

        self.assertGreaterEqual(score, 0.24)
        self.assertGreater(confianca, 0.7)
        self.assertIn("descrições", motivo)

    def test_uma_tag_em_comum_gera_relacao_fraca(self):
        a = evento_fake("trabalho", "dia puxado", tags=["trabalho"], humor=0.2, energia=0.3, estresse=0.8)
        b = evento_fake("reunião", "conversa longa", tags=["trabalho", "rotina"], humor=0.8, energia=0.7, estresse=0.1)

        score, _, motivo = calcular_similaridade(a, b)

        self.assertGreaterEqual(score, 0.10)
        self.assertLess(score, 0.18)
        self.assertIn("tag em comum", motivo)

    def test_mais_tags_em_comum_aumentam_intensidade(self):
        fraca_a = evento_fake("trabalho", "dia puxado", tags=["trabalho"])
        fraca_b = evento_fake("reunião", "conversa longa", tags=["trabalho", "rotina"])
        forte_a = evento_fake("trabalho", "dia puxado", tags=["trabalho", "rotina", "pressão"])
        forte_b = evento_fake("reunião", "conversa longa", tags=["trabalho", "rotina", "pressão"])

        score_fraco, _, _ = calcular_similaridade(fraca_a, fraca_b)
        score_forte, _, motivo_forte = calcular_similaridade(forte_a, forte_b)

        self.assertGreater(score_forte, score_fraco)
        self.assertIn("tags em comum", motivo_forte)

    def test_quatro_dimensoes_iguais_viram_motivo(self):
        a = evento_fake("estado A", "texto", humor=0.6, energia=0.4, estresse=0.2, serenidade=0.7, sensibilidade=0.2, interesse=0.9)
        b = evento_fake("estado B", "outro texto", humor=0.6, energia=0.4, estresse=0.2, serenidade=0.7, sensibilidade=0.8, interesse=0.1)

        score, _, motivo = calcular_similaridade(a, b)

        self.assertGreaterEqual(score, 0.18)
        self.assertIn("4 dimensões iguais", motivo)

    def test_titulos_iguais_geram_relacao(self):
        a = evento_fake("ansiedade", "acordei ansiosa", humor=0.4, energia=0.5, estresse=0.7)
        b = evento_fake("ansiedade", "dia difícil no trabalho", humor=0.3, energia=0.4, estresse=0.8)

        score, _, motivo = calcular_similaridade(a, b)

        self.assertGreater(score, 0.0)
        self.assertIn("título com a mesma intenção", motivo)

    def test_titulos_diferentes_nao_geram_relacao_por_titulo(self):
        a = evento_fake("pilates", "fui malhumorada", humor=0.3, energia=0.5, estresse=0.5)
        b = evento_fake("sono", "dormi mal", humor=0.4, energia=0.4, estresse=0.4)

        score, _, motivo = calcular_similaridade(a, b)

        self.assertNotIn("título", motivo)

    def test_multiplos_motivos_se_somam(self):
        a = evento_fake(
            "foco",
            "continuei os ajustes do app com energia",
            tags=["foco", "app"],
            humor=0.7,
            energia=0.6,
            estresse=0.4,
            serenidade=0.8,
        )
        b = evento_fake(
            "foco",
            "voltei aos ajustes do app e segui concentrada",
            tags=["foco", "app", "rotina"],
            humor=0.7,
            energia=0.6,
            estresse=0.4,
            serenidade=0.8,
        )

        with patch("app.ml.similaridade._embedding_similarity_texto", return_value=0.8):
            score, confianca, motivo = calcular_similaridade(a, b)

        self.assertGreaterEqual(score, 0.50)
        self.assertGreater(confianca, 0.8)
        self.assertIn("tags em comum", motivo)
        self.assertIn("título", motivo)
        self.assertIn("dimensões iguais", motivo)

    def test_descricao_semantica_usa_sentence_transformers_sem_palavras_intermediarias(self):
        a = evento_fake("apresentação", "fiquei nervosa antes da reunião com o time")
        b = evento_fake("reunião", "bati ansiedade antes de falar com a equipe")

        with patch("app.ml.similaridade._embedding_similarity", return_value=0.0):
            with patch("app.ml.similaridade._embedding_similarity_texto", return_value=0.76):
                score, confianca, motivo = calcular_similaridade(a, b)

        self.assertGreaterEqual(score, 0.22)
        self.assertGreater(confianca, 0.8)
        self.assertIn("descrições com sentido/intenção parecidos", motivo)


if __name__ == "__main__":
    unittest.main()
