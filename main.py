import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import requests
import re
import asyncio

from log_config import setup_logging, send_startup_message

# endereço do serviço Node que gera o QR do WhatsApp
# por padrão usa o domínio oficial em produção
WP_API = os.getenv("WP_API", "https://whatsapptest-stij.onrender.com")
# Endpoint para o QR Code; usa o mesmo domínio por padrão
WP_API_QR = os.getenv("WP_API_QR", WP_API)

setup_logging()

import cursos
import cursosom
import secure
import matricular
import alunos
import deletar
import kiwify
import bloquear
import login
import registrar
import auth
import disparos
from app import whatsapp
from backend.app import models as disparo_models
from backend.app.worker import worker_loop
from backend.app.routers import arquivos as arq_r, listas as listas_r, contatos as cont_r, mensagens as msg_r, disparos as disp_r

# ──────────────────────────────────────────────────────────
# Instância da aplicação FastAPI
# ──────────────────────────────────────────────────────────
app = FastAPI(
    title="API CED – Matrícula Automática",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────────────────────────────────────────────────────
# CORS – Domínios permitidos (ajustar via ORIGINS no .env)
# ──────────────────────────────────────────────────────────
origins = [
    origin.strip() for origin in os.getenv("ORIGINS", "*").split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────
# Registro dos roteadores
# ──────────────────────────────────────────────────────────
app.include_router(cursos.router, prefix="/cursos", tags=["Cursos"])
app.include_router(cursosom.router, prefix="/cursosom", tags=["Cursos OM"])
app.include_router(secure.router, tags=["Autenticação"])
app.include_router(matricular.router, prefix="/matricular", tags=["Matrícula"])
app.include_router(alunos.router, prefix="/alunos", tags=["Alunos"])
app.include_router(kiwify.router, prefix="/kiwify", tags=["Kiwify"])
app.include_router(deletar.router, tags=["Excluir Aluno"])
app.include_router(bloquear.router, tags=["Bloqueio"])
app.include_router(login.router, prefix="/login", tags=["Login"])
app.include_router(registrar.router, tags=["Cadastro"])
app.include_router(auth.router)
app.include_router(whatsapp.router)
app.include_router(disparos.router)
app.include_router(arq_r.router)
app.include_router(listas_r.router)
app.include_router(cont_r.router)
app.include_router(msg_r.router)
app.include_router(disp_r.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Preparação inicial do serviço com retries para o banco."""
    send_startup_message()
    await asyncio.to_thread(disparos.wait_for_db)
    await asyncio.to_thread(disparos.ensure_tables)
    await disparo_models.init_db()
    asyncio.create_task(worker_loop())
    yield

app.router.lifespan_context = lifespan


# ──────────────────────────────────────────────────────────
# Health-check
# ──────────────────────────────────────────────────────────
@app.get("/status", tags=["Status"])
def health():
    """Verifica se o serviço está operacional."""
    return {"status": "online", "version": app.version}


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Health-check utilizado pelo Render."""
    ok = await asyncio.to_thread(disparos.check_db)
    if ok:
        return {"status": "ok"}
    raise HTTPException(503, "DB unreachable")


@app.get("/disparo", include_in_schema=False)
@app.get("/disparos", include_in_schema=False)
@app.get("/sistema/disparo", include_in_schema=False)
def legacy_disparo():
    """Compatibilidade com rotas antigas."""
    return RedirectResponse("/sistema")


# ──────────────────────────────────────────────────────────
# Integração com API externa de WhatsApp
# ──────────────────────────────────────────────────────────

@app.get("/qr", include_in_schema=False)
def qr_page():
    """Exibe somente o QR Code atual sem estilos ou scripts."""
    qr = qr_data().get("qr")
    if qr:
        html = f'<html><body><img src="{qr}" alt="QR Code" /></body></html>'
    else:
        html = "<html><body>QR Code indisponível.</body></html>"
    return HTMLResponse(html)


@app.get("/qr/data", include_in_schema=False)
def qr_data():
    """Busca o QR Code atualizado na API externa."""
    try:
        try:
            requests.post(f"{WP_API_QR}/connect", timeout=5)
        except Exception:
            pass
        resp = requests.get(f"{WP_API_QR}/qr", timeout=10)
        if resp.ok:
            try:
                data = resp.json()
                if isinstance(data, dict) and data.get("qr"):
                    return {"qr": data["qr"]}
            except Exception:
                pass
            m = re.search(r'src="(data:[^"]+)"', resp.text)
            if m:
                return {"qr": m.group(1)}
    except Exception:
        pass
    return {"qr": None}


@app.get("/send", tags=["WhatsApp"])
def send_message(para: str, mensagem: str):
    """Envia mensagem simples via API externa."""
    try:
        resp = requests.get(f"{WP_API}/send", params={"para": para, "mensagem": mensagem}, timeout=10)
        if resp.ok:
            return {"success": True}
        raise HTTPException(resp.status_code, resp.text)
    except Exception:
        raise HTTPException(500, "Falha ao enviar mensagem")


static_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


# ──────────────────────────────────────────────────────────
# Execução local / Render
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))  # Render define PORT dinamicamente
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
