# Módulo de Disparos WhatsApp

Este projeto disponibiliza um serviço em FastAPI para gerenciamento e envio de mensagens em massa via WhatsApp.

## Uso rápido

1. Copie `.env.example` para `.env` e ajuste as variáveis do banco de dados.
2. Execute:

```bash
docker compose up --build
```

A interface Web ficará disponível em `http://localhost:8000/sistema/disparo`.

## Exemplos de requisições

### Listas
```bash
curl -X POST http://localhost:8000/api/listas -H 'Content-Type: application/json' -d '{"nome":"Lista 1"}'
```

### Contatos
```bash
curl http://localhost:8000/api/contatos
```

### Mensagens
```bash
curl -X POST http://localhost:8000/api/mensagens -H 'Content-Type: application/json' -d '{"identificador":"padrao","tipo":"texto","conteudo":"Ola"}'
```

### Disparos
```bash
curl -X POST http://localhost:8000/api/disparos -H 'Content-Type: application/json' -d '{"lista_id":1,"mensagem_id":1}'
```
