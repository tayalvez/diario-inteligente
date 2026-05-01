import unittest
from types import SimpleNamespace

from scripts.backfill_embeddings import iter_eventos_sem_embedding
from app.ml.insights_comportamentais import gerar_qualidade_relacoes, gerar_insights_comportamentais
from app.api.insights import _padrao_tema_recorrente, _padrao_relacao_dominante


class BackfillScriptsTest(unittest.TestCase):
    def test_iter_eventos_sem_embedding_filtra_corretamente(self):
        eventos = [
            SimpleNamespace(descricao="texto", embedding=None),
            SimpleNamespace(descricao="   ", embedding=None),
            SimpleNamespace(descricao=None, embedding=None),
            SimpleNamespace(descricao="texto", embedding="[1,2,3]"),
        ]

        filtrados = list(iter_eventos_sem_embedding(eventos))
        self.assertEqual(len(filtrados), 1)
        self.assertEqual(filtrados[0].descricao, "texto")

    def test_qualidade_relacoes_lista_mais_evidentes_nao_depende_so_de_tres_fatores(self):
        evento_a = SimpleNamespace(id=10, evento="desejo", relacoes_origem=[], relacoes_destino=[])
        evento_b = SimpleNamespace(id=12, evento="desenvolvimento do diário", relacoes_origem=[], relacoes_destino=[])
        evento_c = SimpleNamespace(id=14, evento="vela", relacoes_origem=[], relacoes_destino=[])

        relacao_tres_fatores = SimpleNamespace(
            id=1,
            motivo="tags em comum: desejo; título com a mesma intenção: 'desejo'; descrições semanticamente próximas",
            intensidade=0.20,
            confiabilidade=0.80,
            origem_id=10,
            destino_id=11,
            evento_destino=SimpleNamespace(evento="desejo"),
            evento_origem=SimpleNamespace(evento="desejo"),
        )
        relacao_dois_fatores_forte = SimpleNamespace(
            id=2,
            motivo="tag em comum: foco; título com a mesma intenção: 'desenvolvimento do diário'",
            intensidade=0.34,
            confiabilidade=0.8971,
            origem_id=12,
            destino_id=13,
            evento_destino=SimpleNamespace(evento="desenvolvimento do diário"),
            evento_origem=SimpleNamespace(evento="desenvolvimento do diário"),
        )
        relacao_um_fator_fraca = SimpleNamespace(
            id=3,
            motivo="tag em comum: sentimento",
            intensidade=0.12,
            confiabilidade=0.80,
            origem_id=14,
            destino_id=15,
            evento_destino=SimpleNamespace(evento="vela"),
            evento_origem=SimpleNamespace(evento="vela"),
        )

        evento_a.relacoes_origem = [relacao_tres_fatores]
        evento_b.relacoes_origem = [relacao_dois_fatores_forte]
        evento_c.relacoes_origem = [relacao_um_fator_fraca]

        qualidade = gerar_qualidade_relacoes([evento_a, evento_b, evento_c])

        self.assertEqual(qualidade["total"], 3)
        self.assertEqual(len(qualidade["fortes"]), 3)
        self.assertEqual(qualidade["fortes"][0]["par"], "desejo ↔ desejo")
        self.assertTrue(
            any(item["par"] == "desenvolvimento do diário ↔ desenvolvimento do diário" for item in qualidade["fortes"])
        )

    def test_insights_comportamentais_incluem_padroes_do_grafo(self):
        from datetime import datetime, timedelta

        base = datetime(2026, 4, 20, 10, 0, 0)
        eventos = [
            SimpleNamespace(id=1, evento="a", data_hora=base, humor=0.5, energia=0.5, estresse=0.5, relacoes_origem=[], relacoes_destino=[]),
            SimpleNamespace(id=2, evento="b", data_hora=base + timedelta(days=1), humor=0.5, energia=0.5, estresse=0.5, relacoes_origem=[], relacoes_destino=[]),
            SimpleNamespace(id=3, evento="c", data_hora=base + timedelta(days=2), humor=0.5, energia=0.5, estresse=0.5, relacoes_origem=[], relacoes_destino=[]),
            SimpleNamespace(id=4, evento="d", data_hora=base + timedelta(days=3), humor=0.5, energia=0.5, estresse=0.5, relacoes_origem=[], relacoes_destino=[]),
        ]

        relacao_ab = SimpleNamespace(
            id=101,
            motivo="tag em comum: foco; título com a mesma intenção: 'a'",
            intensidade=0.34,
            confiabilidade=1.0,
            origem_id=1,
            destino_id=2,
            evento_origem=SimpleNamespace(evento="a"),
            evento_destino=SimpleNamespace(evento="b"),
        )
        relacao_ac = SimpleNamespace(
            id=102,
            motivo="tag em comum: foco",
            intensidade=0.12,
            confiabilidade=0.8,
            origem_id=1,
            destino_id=3,
            evento_origem=SimpleNamespace(evento="a"),
            evento_destino=SimpleNamespace(evento="c"),
        )

        eventos[0].relacoes_origem = [relacao_ab, relacao_ac]
        eventos[1].relacoes_destino = [relacao_ab]
        eventos[2].relacoes_destino = [relacao_ac]

        insights = gerar_insights_comportamentais(eventos, max_insights=10)
        tipos = {item["tipo"] for item in insights}

        self.assertIn("densidade_relacional_alta", tipos)
        self.assertIn("associacao_dominante", tipos)

    def test_padrao_tema_recorrente_prioriza_tags_e_descricoes(self):
        eventos = [
            SimpleNamespace(tags_json='["trabalho"]', descricao="reunião puxada com o time"),
            SimpleNamespace(tags_json='["trabalho"]', descricao="ajustes no trabalho e prazo"),
            SimpleNamespace(tags_json='["rotina"]', descricao="dia comum"),
        ]

        padrao = _padrao_tema_recorrente(eventos)

        self.assertIsNotNone(padrao)
        self.assertIn(padrao["tipo"], {"tag_recorrente", "termo_recorrente"})
        self.assertNotIn("Estado mais registrado", padrao["titulo"])

    def test_padrao_relacao_dominante_usa_grafo_em_vez_de_frequencia_de_rotulo(self):
        evento_a = SimpleNamespace(id=1, evento="desenvolvimento do diário", relacoes_origem=[], relacoes_destino=[])
        evento_b = SimpleNamespace(id=2, evento="foco", relacoes_origem=[], relacoes_destino=[])

        relacao = SimpleNamespace(
            id=201,
            motivo="tag em comum: foco; título com a mesma intenção: 'desenvolvimento do diário'",
            intensidade=0.34,
            confiabilidade=1.0,
            origem_id=1,
            destino_id=2,
            evento_origem=SimpleNamespace(evento="desenvolvimento do diário"),
            evento_destino=SimpleNamespace(evento="foco"),
        )

        evento_a.relacoes_origem = [relacao]
        evento_b.relacoes_destino = [relacao]

        padrao = _padrao_relacao_dominante([evento_a, evento_b])

        self.assertIsNotNone(padrao)
        self.assertEqual(padrao["tipo"], "relacao_dominante")
        self.assertIn("desenvolvimento do diário ↔ foco", padrao["titulo"])


if __name__ == "__main__":
    unittest.main()
