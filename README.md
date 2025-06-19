# Módulo de Disparo de Mensagens

Este módulo oferece envio de mensagens via WhatsApp integrado ao sistema existente.

## Executar com Docker

1. Copie `.env.example` para `.env` e defina as variáveis de acesso ao PostgreSQL.
2. Inicie os serviços:

```bash
docker compose up --build
```

A API ficará disponível em `http://localhost:8000`.

## Endpoints principais

### Arquivos

```bash
# Upload
curl -F "file=@contatos.csv" http://localhost:8000/api/arquivos
```

### Listas

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"nome":"Clientes"}' http://localhost:8000/api/listas
```

### Contatos

```bash
curl http://localhost:8000/api/contatos?lista_id=1
```

### Mensagens

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"identificador":"Promo","tipo":"texto","conteudo":"Ola"}' \
  http://localhost:8000/api/mensagens
```

### Disparos

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"lista_id":1,"mensagem_id":1,"agendado_para":"2025-01-01T00:00:00"}' \
  http://localhost:8000/api/disparos
```

## Frontend

Abra `frontend/index.html` em seu navegador para utilizar a interface simples.
