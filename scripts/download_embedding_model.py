from pathlib import Path

from sentence_transformers import SentenceTransformer


MODEL_REPO_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TARGET_DIR = Path(__file__).resolve().parents[1] / "models" / "paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    print(f"[embedding] Baixando modelo '{MODEL_REPO_ID}'...")
    model = SentenceTransformer(MODEL_REPO_ID)
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(TARGET_DIR))
    print(f"[embedding] Modelo salvo em: {TARGET_DIR}")


if __name__ == "__main__":
    main()
