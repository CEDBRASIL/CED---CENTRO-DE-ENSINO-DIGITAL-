from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AsyncSessionLocal, Contato
from ..schemas import Contato as ContatoSchema, ContatoCreate

router = APIRouter(prefix="/api/contatos", tags=["Contatos"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("", response_model=ContatoSchema)
async def criar(dados: ContatoCreate, db: AsyncSession = Depends(get_db)):
    contato = Contato(**dados.dict())
    db.add(contato)
    await db.commit()
    await db.refresh(contato)
    return contato

@router.get("", response_model=list[ContatoSchema])
async def listar(lista_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Contato)
    if lista_id:
        q = q.where(Contato.lista_id == lista_id)
    res = await db.execute(q)
    return res.scalars().all()

@router.get("/{cid}", response_model=ContatoSchema)
async def detalhe(cid: int, db: AsyncSession = Depends(get_db)):
    contato = await db.get(Contato, cid)
    if not contato:
        raise HTTPException(404)
    return contato

@router.put("/{cid}", response_model=ContatoSchema)
async def atualizar(cid: int, dados: ContatoCreate, db: AsyncSession = Depends(get_db)):
    contato = await db.get(Contato, cid)
    if not contato:
        raise HTTPException(404)
    for k, v in dados.dict().items():
        setattr(contato, k, v)
    await db.commit()
    await db.refresh(contato)
    return contato

@router.delete("/{cid}")
async def remover(cid: int, db: AsyncSession = Depends(get_db)):
    contato = await db.get(Contato, cid)
    if not contato:
        raise HTTPException(404)
    await db.delete(contato)
    await db.commit()
    return {"ok": True}
