"""
Diário de Eventos — Entry Point
Backend: FastAPI + SQLite com SQLAlchemy
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import criar_tabelas
from app.api import eventos, dashboard, insights, grafo

criar_tabelas()

app = FastAPI(
    title="Diário de Eventos",
    description="Captura e análise de eventos internos com grafo semântico.",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(eventos.router)
app.include_router(dashboard.router)
app.include_router(insights.router)
app.include_router(grafo.router)

static_dir = Path(__file__).parent / "static"


@app.get("/health")
async def health():
    return {"status": "ok", "app": "Diário de Eventos", "versao": "4.0.0"}


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    """Serve arquivos estáticos ou index.html para rotas do Angular."""
    file_path = static_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(static_dir / "index.html"))
