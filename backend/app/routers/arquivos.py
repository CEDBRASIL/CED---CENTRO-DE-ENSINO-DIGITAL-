import os
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from ..models import AsyncSessionLocal, Arquivo

router = APIRouter(prefix="/api/arquivos", tags=["Arquivos"])
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("", response_model=Arquivo)
async def enviar(file: UploadFile = File(...)):
    nome = f"{uuid4().hex}_{file.filename}"
    caminho = os.path.join(UPLOAD_DIR, nome)
    with open(caminho, "wb") as f:
        f.write(await file.read())
    async with AsyncSessionLocal() as session:
        arq = Arquivo(nome_original=file.filename, caminho=caminho)
        session.add(arq)
        await session.commit()
        await session.refresh(arq)
        return arq

@router.get("", response_model=list[Arquivo])
async def listar():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Arquivo))
        return result.scalars().all()

@router.delete("/{arquivo_id}")
async def deletar(arquivo_id: int):
    async with AsyncSessionLocal() as session:
        arq = await session.get(Arquivo, arquivo_id)
        if not arq:
            raise HTTPException(404)
        if os.path.exists(arq.caminho):
            os.remove(arq.caminho)
        await session.delete(arq)
        await session.commit()
    return JSONResponse({"ok": True})
