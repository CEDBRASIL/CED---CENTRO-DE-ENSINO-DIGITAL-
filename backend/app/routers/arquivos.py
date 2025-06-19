import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AsyncSessionLocal, Arquivo
from ..schemas import Arquivo as ArquivoSchema

router = APIRouter(prefix="/api/arquivos", tags=["Arquivos"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/upload", response_model=ArquivoSchema)
async def upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    arq = Arquivo(nome_original=file.filename, caminho=path)
    db.add(arq)
    await db.commit()
    await db.refresh(arq)
    return arq

@router.get("", response_model=list[ArquivoSchema])
async def listar(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Arquivo))
    return res.scalars().all()
