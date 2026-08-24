# Projeto 1 Bimestre - Desenvolvimento de Sistemas para Web

API REST de catálogo de livros usando apenas a biblioteca padrão do Python (`http.server`). Sem dependências externas.

**Integrantes:** Felipe Sarandy, Leticia Lessa e William Zambom.

## Como rodar

```
python servidor.py      # Windows
```

Sobe em `http://localhost:8000` com livros de exemplo já carregados. `CTRL+C` encerra.

Para os testes, com o servidor recém-iniciado em outro terminal:

```
bash testes.sh
```

São 22 casos. Cada um imprime método, URI, dados enviados, status recebido e conteúdo da resposta, e o script termina com `X/22 passaram`.

## Rotas

| Método | URI | Status possíveis |
|---|---|---|
| `GET` | `/api/books` | 200, 500 |
| `POST` | `/api/books` | 201, 400, 500 |
| `PUT` `DELETE` | `/api/books` | 405 |
| `GET` | `/api/books/{id}` | 200, 400, 404, 500 |
| `PUT` | `/api/books/{id}` | 200, 400, 404, 500 |
| `DELETE` | `/api/books/{id}` | 204, 400, 404, 500 |
| `POST` | `/api/books/{id}` | 405 |
| qualquer | outra rota | 404 |
| método não implementado | qualquer rota | 501 |

O `201` traz o header `Location` com a URI do livro criado. Todo `405` traz o header `Allow` com os métodos aceitos naquela rota.

## Formato de um livro

```json
{
  "id": 1,
  "title": "Dom Casmurro",
  "author": "Machado de Assis",
  "year": 1899,
  "available": true
}
```

`title` e `author` são obrigatórios e precisam ser texto não vazio. `year` é inteiro e `available` é booleano, com `true` como padrão. Qualquer outro campo é recusado.

## Formato de erro

```json
{
  "erro": "Dados do livro inválidos.",
  "detalhes": [
    "O campo 'title' é obrigatório e deve ser um texto não vazio."
  ]
}
```

`detalhes` só aparece quando há o que detalhar. Respostas de sucesso não usam envelope: devolvem a lista ou o objeto puro. Tudo sai como `application/json; charset=utf-8`, exceto o `204`, que não tem corpo. Nenhuma resposta sai em HTML.