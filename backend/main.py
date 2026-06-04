import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import init_db
from routers.webhook import router as webhook_router
from routers.api import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    logger.info("Gonzalo Agentes IA — Marketing Agent ready")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Gonzalo Agentes IA",
    description="Plataforma de agentes IA para negocios en Lima",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(api_router)

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")
    demos_dir = os.path.join(frontend_dir, "demos")
    if os.path.isdir(demos_dir):
        app.mount("/demos", StaticFiles(directory=demos_dir, html=True), name="demos")

    # Landing page = pagina principal publica
    @app.get("/")
    async def serve_landing():
        return FileResponse(os.path.join(frontend_dir, "landing.html"))

    # Dashboard de marketing = panel privado con login
    @app.get("/dashboard")
    async def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "gonzalo-agentes-ia", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
