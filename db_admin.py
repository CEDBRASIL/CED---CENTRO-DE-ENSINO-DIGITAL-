import argparse
import psycopg2
from psycopg2.extras import RealDictCursor

# Configurações diretas do banco de dados
PG_HOST = 'dpg-d1a3bpngi27c73f2s4s0-a.oregon-postgres.render.com'
PG_PORT = '5432'
PG_DB = 'ced_database_ec01'
PG_USER = 'yuri'
PG_PASS = 'Wz60DamitHUcXWJV5G61V7SAiWjsB5vl'


def get_conn():
    """Abre conexão com o banco usando as credenciais fixas."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        sslmode='require'
    )


def criar_tabelas() -> None:
    """Cria as tabelas principais caso não existam."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listas (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                descricao TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS contatos (
                id SERIAL PRIMARY KEY,
                lista_id INTEGER REFERENCES listas(id),
                nome TEXT,
                telefone TEXT NOT NULL,
                desc1 TEXT,
                desc2 TEXT,
                desc3 TEXT
            );
            """
        )
        conn.commit()


def listar_listas():
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM listas ORDER BY id")
        return cur.fetchall()


def listar_contatos():
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM contatos ORDER BY id")
        return cur.fetchall()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Administração do banco de dados')
    sub = parser.add_subparsers(dest='cmd')
    sub.add_parser('init', help='Criar tabelas')
    sub.add_parser('listas', help='Listar listas')
    sub.add_parser('contatos', help='Listar contatos')

    args = parser.parse_args()

    if args.cmd == 'init':
        criar_tabelas()
        print('Tabelas criadas.')
    elif args.cmd == 'listas':
        for l in listar_listas():
            print(l)
    elif args.cmd == 'contatos':
        for c in listar_contatos():
            print(c)
    else:
        parser.print_help()
