## Projeto 1 Bimestre - Desenvolvimento de Sistemas para Web

API REST de catálogo de livros usando apenas a biblioteca padrão do Python (`http.server`). Sem dependências externas.

**Integrantes:** _(preencher)_

## Como rodar

```
python servidor.py      # Windows
python3 servidor.py     # Linux e macOS
```

Sobe em `http://localhost:8000` com três livros de exemplo. `CTRL+C` encerra.

Para os testes, com o servidor rodando em outro terminal:

```
bash testes.sh
```

São 26 casos cobrindo os caminhos felizes e todos os erros. O script compara o status esperado com o obtido, confere os headers `Location` e `Allow`, e termina com `X/26 passaram`. Rode com o servidor recém-iniciado, porque os casos dependem dos ids 1, 2 e 3 de exemplo e da ordem de execução.

## Recursos

| Método | `/livros` | `/livros/{id}` |
|---|---|---|
| `GET` | lista os livros | retorna um livro |
| `POST` | cria um livro | — |
| `PUT` | — | substitui o livro por inteiro |
| `DELETE` | — | remove o livro |
| `HEAD` | headers do `GET`, sem corpo | headers do `GET`, sem corpo |
| `OPTIONS` | métodos aceitos em `Allow` | métodos aceitos em `Allow` |

## Códigos de status

| Código | Quando |
|---|---|
| `200` | `GET` ou `PUT` bem-sucedido |
| `201` | `POST` criou o livro; traz `Location: /livros/{id}` |
| `204` | `DELETE` ou `OPTIONS`; sem corpo |
| `400` | erro sintático: JSON malformado, corpo vazio, corpo que não é objeto, `Content-Length` inválido |
| `404` | rota inexistente ou id não encontrado |
| `405` | método não aceito na rota; sempre com header `Allow` |
| `415` | `Content-Type` não é `application/json` |
| `422` | erro semântico: JSON válido, mas os dados reprovam em `validar_livro()` |
| `500` | exceção inesperada; traceback fica só no console |
| `501` | verbo HTTP desconhecido (`TRACE`, `CONNECT`) |

## Formato de erro

```json
{
  "erro": {
    "status": 422,
    "mensagem": "Dados do livro inválidos.",
    "detalhes": ["Campos não reconhecidos: editora."]
  }
}
```

`detalhes` vem vazio quando não há o que detalhar. Respostas de sucesso não usam envelope: devolvem a lista ou o objeto puro. Tudo sai como `application/json; charset=utf-8`, exceto o `204`. Nenhuma resposta sai em HTML.

## Decisões

**400 vs. 422.** `400` é o corpo que o servidor não consegue interpretar; `422` é o corpo interpretado que descreve um livro impossível (título vazio, ano como texto, campo desconhecido). O cliente descobre se o problema é como ele serializou ou o que ele pediu.

**`/livros/abc` devolve 404.** O segmento depois de `/livros/` só vira recurso se for inteiro. `abc` não é um id errado, é um endereço que não existe.

**`PATCH` devolve 405.** Atualização parcial exigiria uma validação diferente de `validar_livro()`, que sempre cobra os campos obrigatórios. Um PATCH pela metade seria pior que nenhum.

**`Content-Length` negativo é recusado.** `rfile.read(-1)` leria até o fim do socket e travaria o servidor, que é single-thread.

**`send_error` foi sobrescrito.** A stdlib responde HTML nos erros que ela levanta antes de chegar num `do_*`, o que quebraria o contrato JSON justamente no caminho de erro.