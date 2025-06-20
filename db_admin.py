import argparse
import asyncio

from backend.app.models import (
    AsyncSessionLocal,
    Lista,
    Contato,
    init_db,
)
from sqlalchemy import select


async def criar_lista(nome: str, descricao: str | None = None) -> int:
    """Cria uma nova lista e retorna seu ID."""
    async with AsyncSessionLocal() as session:
        lista = Lista(nome=nome, descricao=descricao)
        session.add(lista)
        await session.commit()
        await session.refresh(lista)
        return lista.id


async def listar_listas() -> list[Lista]:
    """Retorna todas as listas cadastradas."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Lista))
        return res.scalars().all()


async def criar_contato(
    lista_id: int,
    telefone: str,
    nome: str | None = None,
    desc1: str | None = None,
    desc2: str | None = None,
    desc3: str | None = None,
) -> int:
    """Cria um contato associado a uma lista."""
    async with AsyncSessionLocal() as session:
        contato = Contato(
            lista_id=lista_id,
            telefone=telefone,
            nome=nome,
            desc1=desc1,
            desc2=desc2,
            desc3=desc3,
        )
        session.add(contato)
        await session.commit()
        await session.refresh(contato)
        return contato.id


async def listar_contatos(lista_id: int | None = None) -> list[Contato]:
    """Lista os contatos, podendo filtrar por lista."""
    async with AsyncSessionLocal() as session:
        query = select(Contato)
        if lista_id is not None:
            query = query.where(Contato.lista_id == lista_id)
        res = await session.execute(query)
        return res.scalars().all()


async def _init() -> None:
    """Garante que as tabelas existam."""
    await init_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Administração do banco de dados")
    sub = parser.add_subparsers(dest="cmd")

    sl = sub.add_parser("criar-lista", help="Cria uma nova lista")
    sl.add_argument("nome")
    sl.add_argument("-d", "--descricao", default=None)

    cl = sub.add_parser("listar-listas", help="Lista todas as listas")

    sc = sub.add_parser("criar-contato", help="Cria um contato")
    sc.add_argument("lista_id", type=int)
    sc.add_argument("telefone")
    sc.add_argument("-n", "--nome", default=None)
    sc.add_argument("--desc1", default=None)
    sc.add_argument("--desc2", default=None)
    sc.add_argument("--desc3", default=None)

    lc = sub.add_parser("listar-contatos", help="Lista os contatos")
    lc.add_argument("-l", "--lista-id", type=int, default=None)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    asyncio.run(_init())

    if args.cmd == "criar-lista":
        lid = asyncio.run(criar_lista(args.nome, args.descricao))
        print(f"Lista criada com ID {lid}")
    elif args.cmd == "listar-listas":
        listas = asyncio.run(listar_listas())
        for l in listas:
            print(f"{l.id}: {l.nome}")
    elif args.cmd == "criar-contato":
        cid = asyncio.run(
            criar_contato(
                lista_id=args.lista_id,
                telefone=args.telefone,
                nome=args.nome,
                desc1=args.desc1,
                desc2=args.desc2,
                desc3=args.desc3,
            )
        )
        print(f"Contato criado com ID {cid}")
    elif args.cmd == "listar-contatos":
        contatos = asyncio.run(listar_contatos(args.lista_id))
        for c in contatos:
            print(f"{c.id}: {c.telefone} ({c.nome})")


if __name__ == "__main__":
    main()
