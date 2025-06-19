from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..models import AsyncSessionLocal, Disparo
from ..schemas import Disparo as DisparoSchema, DisparoCreate

router = APIRouter(prefix="/api/disparos", tags=["Disparos"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("", response_model=DisparoSchema)
async def criar(payload: DisparoCreate, db: AsyncSession = Depends(get_db)):
    disp = Disparo(**payload.dict())
    db.add(disp)
    await db.commit()
    await db.refresh(disp)
    return disp

@router.get("", response_model=list[DisparoSchema])
async def listar(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Disparo))
    return res.scalars().all()

@router.get("/{did}", response_model=DisparoSchema)
async def detalhe(did: int, db: AsyncSession = Depends(get_db)):
    disp = await db.get(Disparo, did)
    if not disp:
        raise HTTPException(404)
    return disp
