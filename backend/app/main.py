import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .worker import worker_loop
from .routers import arquivos, listas, contatos, mensagens, disparos

app = FastAPI(title="Modulo Disparos")

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
async def startup_event():
    asyncio.create_task(worker_loop())
