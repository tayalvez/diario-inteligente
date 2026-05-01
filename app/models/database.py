"""Módulo de banco de dados — modelos SQLAlchemy com SQLite."""
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import (
    create_engine, Column, Integer, Float, Text,
    DateTime, ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TypeDecorator

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'diario.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class JSONType(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value, ensure_ascii=False, default=str) if value is not None else None

    def process_result_value(self, value, dialect):
        return json.loads(value) if value is not None else None


class Evento(Base):
    """Evento — registro de uma ocorrência com estado interno."""
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True, index=True)
    evento = Column(Text, nullable=False, index=True)          # "cansada", "estressada"
    data_hora = Column(DateTime, nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    contexto_json = Column(Text, nullable=True)                # JSON {"local": "trabalho"}
    tags_json = Column(Text, nullable=True)                    # JSON ["trabalho", "pressão"]
    dimensoes_extras_json = Column(Text, nullable=True)        # JSON {"foco": 0.7}
    # Dimensões obrigatórias (escala 0.0–1.0)
    energia = Column(Float, nullable=False)
    humor = Column(Float, nullable=False)
    estresse = Column(Float, nullable=False)
    sensibilidade = Column(Float, nullable=False, default=0.5)
    serenidade = Column(Float, nullable=False, default=0.5)
    interesse = Column(Float, nullable=False, default=0.5)
    # Metadados temporais (derivados de data_hora)
    hora = Column(Integer, nullable=True)        # 0–23
    dia_semana = Column(Integer, nullable=True)  # 0–6
    # Análise semântica (opcional)
    sentimento_score = Column(Float, nullable=True)
    conceitos_json = Column(Text, nullable=True)
    embedding = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    relacoes_origem = relationship(
        "RelacaoEvento", foreign_keys="RelacaoEvento.origem_id",
        back_populates="evento_origem", cascade="all, delete-orphan",
    )
    relacoes_destino = relationship(
        "RelacaoEvento", foreign_keys="RelacaoEvento.destino_id",
        back_populates="evento_destino", cascade="all, delete-orphan",
    )


class RelacaoEvento(Base):
    """Relação entre dois eventos — aresta do grafo."""
    __tablename__ = "relacoes_evento"
    id = Column(Integer, primary_key=True, index=True)
    origem_id = Column(Integer, ForeignKey("eventos.id", ondelete="CASCADE"), nullable=False, index=True)
    destino_id = Column(Integer, ForeignKey("eventos.id", ondelete="CASCADE"), nullable=False, index=True)
    intensidade = Column(Float, default=0.5, nullable=False)      # 0.0–1.0: força da relação
    confiabilidade = Column(Float, default=1.0, nullable=False)   # 0.0–1.0: 1.0=manual, menor=automático
    motivo = Column(Text, nullable=True)                          # explicação legível de por que a relação existe
    criado_em = Column(DateTime, default=datetime.utcnow)

    evento_origem = relationship("Evento", foreign_keys=[origem_id], back_populates="relacoes_origem")
    evento_destino = relationship("Evento", foreign_keys=[destino_id], back_populates="relacoes_destino")


class InsightGerado(Base):
    __tablename__ = "insights_gerados"
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Text, nullable=False)
    titulo = Column(Text, nullable=False)
    descricao = Column(Text, nullable=False)
    dados_json = Column(JSONType, default=dict)
    relevancia = Column(Float, default=0.5)
    gerado_em = Column(DateTime, default=datetime.utcnow)


_COLUNAS_ESPERADAS = {"evento", "data_hora", "energia", "humor", "estresse",
                      "contexto_json", "tags_json", "dimensoes_extras_json"}
_TABELAS_ESPERADAS = {"eventos", "relacoes_evento", "insights_gerados"}


def criar_tabelas():
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tabelas_iniciais = set(inspector.get_table_names())

    if "eventos" in tabelas_iniciais:
        cols_eventos = {c["name"] for c in inspector.get_columns("eventos")}
        schema_ok = (
            _COLUNAS_ESPERADAS.issubset(cols_eventos)
            and _TABELAS_ESPERADAS.issubset(tabelas_iniciais)
        )
        if not schema_ok:
            print("[db] Schema desatualizado — recriando banco de dados...")
            Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    # Migrações incrementais — adiciona colunas novas sem recriar o banco
    inspector = inspect(engine)
    tabelas_atuais = set(inspector.get_table_names())
    with engine.connect() as conn:
        cols_relacoes = {c["name"] for c in inspector.get_columns("relacoes_evento")} if "relacoes_evento" in tabelas_atuais else set()
        if "motivo" not in cols_relacoes:
            conn.execute(__import__("sqlalchemy").text("ALTER TABLE relacoes_evento ADD COLUMN motivo TEXT"))
            conn.commit()

        cols_eventos = {c["name"] for c in inspector.get_columns("eventos")} if "eventos" in tabelas_atuais else set()
        for nova_coluna in ("sensibilidade", "serenidade", "interesse"):
            if nova_coluna not in cols_eventos:
                conn.execute(__import__("sqlalchemy").text(
                    f"ALTER TABLE eventos ADD COLUMN {nova_coluna} REAL NOT NULL DEFAULT 0.5"
                ))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
