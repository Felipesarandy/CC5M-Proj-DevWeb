## Projeto 1 Bimestre - Desenvolvimento de Sistemas para Web

API REST de catálogo de livros usando apenas a biblioteca padrão do Python
(`http.server`). Sem dependências externas.

## Como rodar o servidor

Windows:

```
cd D:\UVV\DevWeb1B\CC5M-Proj-DevWeb
python servidor.py
```

Linux e macOS:

```
cd CC5M-Proj-DevWeb
python3 servidor.py
```

O servidor sobe em `http://localhost:8000` já com três livros de exemplo
carregados por `carregar_dados_exemplo()`. `CTRL+C` encerra.

## Recursos e métodos

| Método    | URI            | Efeito                                  |
|-----------|----------------|-----------------------------------------|
| `GET`     | `/livros`      | Lista todos os livros                   |
| `POST`    | `/livros`      | Cria um livro                           |
| `GET`     | `/livros/{id}` | Retorna um livro                        |
| `PUT`     | `/livros/{id}` | Substitui um livro por inteiro          |
| `DELETE`  | `/livros/{id}` | Remove um livro                         |
| `HEAD`    | ambas          | Mesmos headers do `GET`, sem corpo      |
| `OPTIONS` | ambas          | Anuncia os métodos aceitos em `Allow`   |

## Códigos de status

| Código | Quando é devolvido                                                          |
|--------|-----------------------------------------------------------------------------|
| `200`  | `GET` ou `PUT` bem-sucedido                                                  |
| `201`  | `POST` criou o livro; traz o header `Location: /livros/{id}`                  |
| `204`  | `DELETE` removeu o livro, ou `OPTIONS` respondeu; sem corpo                   |
| `400`  | Erro **sintático**: JSON malformado, corpo vazio, corpo que não é objeto JSON, `Content-Length` ausente, não numérico, negativo ou acima de 1 MiB |
| `404`  | Rota inexistente, ou livro com aquele id não existe                          |
| `405`  | Método não aceito naquela rota; sempre acompanhado do header `Allow`          |
| `415`  | `Content-Type` da requisição não é `application/json`                        |
| `422`  | Erro **semântico**: o JSON é válido, mas os dados do livro não passam em `validar_livro()` |
| `500`  | Exceção inesperada; o traceback fica só no console do servidor               |
| `501`  | Verbo HTTP desconhecido pelo servidor (`TRACE`, `CONNECT`, etc.)             |

## Formato do JSON de erro

Toda resposta de erro usa o mesmo envelope, com `detalhes` vazio quando não há
nada a detalhar:

```json
{
  "erro": {
    "status": 422,
    "mensagem": "Dados do livro inválidos.",
    "detalhes": [
      "O campo 'titulo' é obrigatório e deve ser um texto não vazio.",
      "Campos não reconhecidos: editora."
    ]
  }
}
```

As respostas de sucesso **não** usam envelope: `GET /livros` devolve a lista
pura e `GET /livros/{id}` devolve o objeto puro.

Toda resposta sai como `Content-Type: application/json; charset=utf-8`, exceto
o `204`, que por definição não tem corpo nem `Content-Type`. Nenhuma resposta
sai em HTML.

## Como rodar os testes

Com o servidor rodando em outro terminal:

```
bash testes.sh
```

São 26 casos cobrindo os caminhos felizes e todos os erros acima. O script
imprime status esperado versus obtido, confere os headers `Location` e `Allow`,
verifica que o `HEAD` não traz corpo e termina com `X/26 passaram`. Ele depende
do servidor ter acabado de subir, porque conta com os ids 1, 2 e 3 de exemplo e
com a ordem dos casos.

## Decisões de projeto

**400 versus 422.** Os dois significam coisas diferentes. `400` é o corpo que o
servidor não consegue nem interpretar: JSON quebrado, corpo vazio, um array no
lugar de um objeto, `Content-Length` inválido. `422` é o corpo que foi
interpretado sem problemas mas descreve um livro impossível: título vazio, ano
como texto, campo obrigatório faltando, campo desconhecido. Separar os dois deixa
o cliente saber se o problema é como ele serializou o pedido ou o que ele pediu.

**`/livros/abc` devolve 404, não 400.** O path só vira recurso quando o segmento
depois de `/livros/` é um inteiro. `abc` não corresponde a recurso nenhum nesta
API, então é o mesmo caso de `/rota-inexistente`. Não é um id errado, é um
endereço que não existe.

**`PATCH` devolve 405.** Atualização parcial exigiria uma validação diferente da
de `validar_livro()`, que cobra os campos obrigatórios sempre. Entregar um PATCH
pela metade seria pior que não ter PATCH, então a rota responde `405` com o
header `Allow` dizendo o que ela realmente aceita.

**`Content-Length` negativo é recusado.** `rfile.read(-1)` leria até o fim do
socket e travaria o servidor, que é single-thread — uma requisição só derrubaria
a API para todo mundo.

**`send_error` foi sobrescrito.** A stdlib responde HTML nos erros que ela mesma
levanta antes de chegar num `do_*` (verbo desconhecido, linha de pedido
inválida). Sem sobrescrever, a API quebraria o próprio contrato JSON justamente
no caminho de erro.
