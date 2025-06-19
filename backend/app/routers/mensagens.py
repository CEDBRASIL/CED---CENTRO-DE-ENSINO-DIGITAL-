from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AsyncSessionLocal, Mensagem
from ..schemas import Mensagem as MensagemSchema, MensagemCreate

router = APIRouter(prefix="/api/mensagens", tags=["Mensagens"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("", response_model=MensagemSchema)
async def criar(dados: MensagemCreate, db: AsyncSession = Depends(get_db)):
    msg = Mensagem(**dados.dict())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

@router.get("", response_model=list[MensagemSchema])
async def listar(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Mensagem))
    return res.scalars().all()

@router.get("/{mid}", response_model=MensagemSchema)
async def detalhe(mid: int, db: AsyncSession = Depends(get_db)):
    msg = await db.get(Mensagem, mid)
    if not msg:
        raise HTTPException(404)
    return msg

@router.put("/{mid}", response_model=MensagemSchema)
async def atualizar(mid: int, dados: MensagemCreate, db: AsyncSession = Depends(get_db)):
    msg = await db.get(Mensagem, mid)
    if not msg:
        raise HTTPException(404)
    for k, v in dados.dict().items():
        setattr(msg, k, v)
    await db.commit()
    await db.refresh(msg)
    return msg

@router.delete("/{mid}")
async def remover(mid: int, db: AsyncSession = Depends(get_db)):
    msg = await db.get(Mensagem, mid)
    if not msg:
        raise HTTPException(404)
    await db.delete(msg)
    await db.commit()
    return {"ok": True}
