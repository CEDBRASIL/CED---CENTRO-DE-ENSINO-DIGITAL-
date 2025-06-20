import argparse
import asyncio

from backend.app.models import init_db, AsyncSessionLocal, Lista, Contato
from sqlalchemy import select

async def cmd_init_db(_):
    await init_db()
    print("Tabelas criadas ou já existentes.")

async def cmd_add_lista(args):
    async with AsyncSessionLocal() as db:
        lista = Lista(nome=args.nome, descricao=args.descricao)
        db.add(lista)
        await db.commit()
        await db.refresh(lista)
        print(f"Lista criada com id {lista.id}")

async def cmd_list_listas(_):
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Lista))
        for l in res.scalars():
            print(f"{l.id}: {l.nome} - {l.descricao or ''}")

async def cmd_add_contato(args):
    async with AsyncSessionLocal() as db:
        cont = Contato(
            lista_id=args.lista_id,
            nome=args.nome,
            telefone=args.telefone,
            desc1=args.desc1,
            desc2=args.desc2,
            desc3=args.desc3,
        )
        db.add(cont)
        await db.commit()
        await db.refresh(cont)
        print(f"Contato criado com id {cont.id}")

async def cmd_list_contatos(args):
    async with AsyncSessionLocal() as db:
        q = select(Contato)
        if args.lista_id:
            q = q.where(Contato.lista_id == args.lista_id)
        res = await db.execute(q)
        for c in res.scalars():
            print(f"{c.id}: {c.telefone} - {c.nome or ''}")

async def main():
    parser = argparse.ArgumentParser(description="Administração do banco de dados")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")

    p_add_lista = sub.add_parser("add-lista")
    p_add_lista.add_argument("nome")
    p_add_lista.add_argument("--descricao")

    sub.add_parser("list-listas")

    p_add_contato = sub.add_parser("add-contato")
    p_add_contato.add_argument("lista_id", type=int)
    p_add_contato.add_argument("telefone")
    p_add_contato.add_argument("--nome")
    p_add_contato.add_argument("--desc1")
    p_add_contato.add_argument("--desc2")
    p_add_contato.add_argument("--desc3")

    p_list_contatos = sub.add_parser("list-contatos")
    p_list_contatos.add_argument("--lista_id", type=int)

    args = parser.parse_args()

    if args.cmd == "init-db":
        await cmd_init_db(args)
    elif args.cmd == "add-lista":
        await cmd_add_lista(args)
    elif args.cmd == "list-listas":
        await cmd_list_listas(args)
    elif args.cmd == "add-contato":
        await cmd_add_contato(args)
    elif args.cmd == "list-contatos":
        await cmd_list_contatos(args)

if __name__ == "__main__":
    asyncio.run(main())
