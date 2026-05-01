import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.ml import nlp


class NlpConfigTest(unittest.TestCase):
    def test_usa_diretorio_local_do_projeto_quando_existente(self):
        with patch.dict(os.environ, {}, clear=False):
            with patch.object(nlp, "MODEL_LOCAL_DIR", Path("/tmp/modelo-local")):
                with patch.object(Path, "exists", return_value=True):
                    self.assertEqual(nlp.resolver_fonte_modelo(), "/tmp/modelo-local")

    def test_usa_variavel_embedding_model_dir_quando_valida(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"EMBEDDING_MODEL_DIR": temp_dir}, clear=False):
                resolved = nlp.resolver_fonte_modelo()
                self.assertEqual(resolved, str(Path(temp_dir).resolve()))

    def test_falha_sem_modelo_local_e_sem_download_remoto(self):
        with patch.dict(os.environ, {}, clear=False):
            with patch.object(nlp, "MODEL_LOCAL_DIR", Path("/tmp/modelo-ausente")):
                with patch.object(Path, "exists", return_value=False):
                    with self.assertRaises(RuntimeError):
                        nlp.resolver_fonte_modelo()


if __name__ == "__main__":
    unittest.main()
