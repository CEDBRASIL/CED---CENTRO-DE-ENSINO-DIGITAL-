from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import arquivos, listas, contatos, mensagens, disparos

app = FastAPI(title="Disparos WhatsApp")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(arquivos.router)
app.include_router(listas.router)
app.include_router(contatos.router)
app.include_router(mensagens.router)
app.include_router(disparos.router)


@app.on_event("startup")
async def startup():
    pass
