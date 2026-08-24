# Projeto 1 Bimestre - Desenvolvimento de Sistemas para Web

API REST de catálogo de livros usando apenas a biblioteca padrão do Python (`http.server`). Sem dependências externas.

**Integrantes:** Felipe Sarandy, Leticia Lessa e William Zambom.

## Como rodar

```
python servidor.py      # Windows
python3 servidor.py     # Linux e macOS
```

Sobe em `http://localhost:8000` com três livros de exemplo já carregados. `CTRL+C` encerra.

Para os testes, com o servidor recém-iniciado em outro terminal:

```
bash testes.sh
```

São 22 casos. Cada um imprime método, URI, dados enviados, status recebido e conteúdo da resposta, e o script termina com `X/22 passaram`. A saída da última execução está em `evidencias.txt`.

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

## Decisões de projeto

**1. Por que `/api/books/1` é um recurso diferente de `/api/books`.**
`/api/books` é a coleção inteira; `/api/books/1` é um livro específico dentro dela. São coisas distintas, então aceitam métodos distintos: não faz sentido dar `DELETE` na coleção, nem `POST` num livro que já existe.

**2. Por que `GET` é usado para consultar.**
`GET` só lê, não altera nada no servidor. Por isso pode ser repetido à vontade, guardado em cache e chamado direto pela barra do navegador, sem risco de mudar o catálogo por acidente.

**3. Por que `POST` é usado para criar.**
`POST` é o método que não é idempotente: cada chamada cria um livro novo, com um id novo. É justamente o que se espera de uma criação — dois `POST` iguais devolvem `/api/books/4` e `/api/books/5`, não o mesmo recurso duas vezes.

**4. Diferença entre `400 Bad Request` e `404 Not Found`.**
`400` é problema no que o cliente mandou: JSON quebrado, corpo vazio, campo obrigatório faltando, id que não é inteiro. `404` é problema no que ele pediu: a rota não existe ou o livro daquele id não está no catálogo. No `400` o pedido está errado; no `404` o pedido está certo mas o alvo não existe.

**5. Por que a exclusão retorna `204 No Content`.**
A remoção deu certo e não sobrou nada para devolver — o livro deixou de existir. `204` diz exatamente isso: sucesso, sem corpo. Devolver `200` com um JSON vazio ou com o livro apagado seria informação inútil.

**6. O que acontece com os livros se o servidor for encerrado.**
Tudo se perde. Os dados vivem no dicionário `_livros` em `livros_dados.py`, que só existe na memória do processo. Ao reiniciar, `carregar_dados_exemplo()` roda de novo e o catálogo volta aos mesmos três livros iniciais, com os ids recomeçando do 1.

**7. Limitações de manter os dados só em memória.**
Não há persistência: nada sobrevive a um reinício ou a uma queda. Não dá para rodar mais de uma instância, porque cada processo teria o próprio catálogo. O consumo de memória cresce com o número de livros, sem limite, e o servidor é single-thread, então uma requisição por vez. Para um trabalho de aula serve; em produção o lugar dos dados seria um banco.
