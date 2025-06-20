from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

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


@router.post("/importar/{lista_id}", response_model=dict)
async def importar(lista_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Importa contatos de um arquivo CSV ou Excel para a lista especificada."""
    nome = file.filename.lower()
    if nome.endswith(".csv"):
        df = pd.read_csv(file.file)
    else:
        df = pd.read_excel(file.file)
    total = 0
    for _, row in df.iterrows():
        telefone = str(row.get("telefone") or row.get("numero") or "").strip()
        if not telefone:
            continue
        contato = Contato(
            lista_id=lista_id,
            nome=row.get("nome"),
            telefone=telefone,
            desc1=row.get("desc1"),
            desc2=row.get("desc2"),
            desc3=row.get("desc3"),
        )
        db.add(contato)
        total += 1
    await db.commit()
    return {"importados": total}


@router.post("/adicionar_numeros/{lista_id}", response_model=dict)
async def adicionar_numeros(lista_id: int, numeros: list[str] = Body(...), db: AsyncSession = Depends(get_db)):
    """Adiciona uma lista de números simples à lista informada."""
    total = 0
    for num in numeros:
        telefone = str(num).strip()
        if not telefone:
            continue
        contato = Contato(lista_id=lista_id, telefone=telefone)
        db.add(contato)
        total += 1
    await db.commit()
    return {"importados": total}
