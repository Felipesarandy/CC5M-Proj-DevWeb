#!/usr/bin/env bash
# Suite de testes com curl da API de catalogo de livros.
# Precisa do servidor recem-iniciado, porque os casos contam com os ids 1, 2 e 3
# criados por carregar_dados_exemplo e com a ordem em que aparecem aqui.
#
#   Terminal 1:  python servidor.py
#   Terminal 2:  bash testes.sh

BASE="http://localhost:8000"
JSON="Content-Type: application/json"

CORPO=$(mktemp)
CABECALHOS=$(mktemp)
trap 'rm -f "$CORPO" "$CABECALHOS"' EXIT

TOTAL=0
PASSOU=0

# verificar <descricao> <metodo> <uri> <dados> <esperado> <exigido> [args extras do curl]
# <dados> aceita "-" para requisicao sem corpo
# <exigido> aceita "-", "Location", "Allow" ou "sem-corpo"
verificar() {
    descricao="$1"
    metodo="$2"
    uri="$3"
    dados="$4"
    esperado="$5"
    exigido="$6"
    shift 6

    TOTAL=$((TOTAL + 1))

    if [ "$dados" = "-" ]; then
        set -- -X "$metodo" "$BASE$uri" "$@"
    else
        set -- -X "$metodo" "$BASE$uri" -H "$JSON" -d "$dados" "$@"
    fi

    resposta=$(curl -s -o "$CORPO" -D "$CABECALHOS" -w '%{http_code}|%{size_download}' \
        --max-time 6 "$@")

    obtido=${resposta%%|*}
    baixado=${resposta##*|}

    ok="sim"
    extra=""

    if [ "$obtido" != "$esperado" ]; then
        ok="nao"
    fi

    case "$exigido" in
        Location|Allow)
            valor=$(grep -i "^$exigido:" "$CABECALHOS" | head -1 | tr -d '\r' | cut -d' ' -f2-)
            if [ -z "$valor" ]; then
                ok="nao"
                extra="$exigido AUSENTE"
            else
                extra="$exigido: $valor"
            fi
            ;;
        sem-corpo)
            if [ "$baixado" != "0" ]; then
                ok="nao"
                extra="corpo deveria estar vazio, veio $baixado bytes"
            else
                extra="corpo vazio, como esperado"
            fi
            ;;
    esac

    if [ "$ok" = "sim" ]; then
        PASSOU=$((PASSOU + 1))
        resultado="OK"
    else
        resultado="FALHOU"
    fi

    echo "[$TOTAL] $descricao"
    echo "     Metodo:   $metodo"
    echo "     URI:      $uri"

    if [ "$dados" = "-" ]; then
        echo "     Enviado:  (sem corpo)"
    else
        echo "     Enviado:  $dados"
    fi

    echo "     Status:   $obtido (esperado $esperado) -> $resultado"

    if [ -n "$extra" ]; then
        echo "     Header:   $extra"
    fi

    echo "     Resposta: $(tr -d '\r\n' < "$CORPO" | tr -s ' ')"
    echo
}

if ! curl -s -o /dev/null --max-time 5 "$BASE/api/books"; then
    echo "Servidor nao respondeu em $BASE. Rode 'python servidor.py' antes." >&2
    exit 1
fi

echo "Suite de testes - API de catalogo de livros"
echo "Base: $BASE"
echo

echo "--- LEITURA ---"
verificar "Lista a colecao" GET /api/books - 200 -
verificar "Consulta um livro" GET /api/books/1 - 200 -
verificar "Livro inexistente" GET /api/books/999 - 404 -
verificar "Id que nao e inteiro" GET /api/books/abc - 400 -
verificar "Rota inexistente" GET /rota-inexistente - 404 -

echo "--- CRIACAO ---"
verificar "Cria um livro" POST /api/books \
    '{"title":"Vidas Secas","author":"Graciliano Ramos","year":1938,"available":true}' 201 Location
verificar "JSON malformado" POST /api/books '{"title":' 400 -
verificar "Corpo vazio" POST /api/books '' 400 -
verificar "Corpo que nao e objeto" POST /api/books '[1,2]' 400 -
verificar "Sem o campo title" POST /api/books '{"author":"Alguem"}' 400 -
verificar "Title vazio" POST /api/books '{"title":"","author":"Alguem"}' 400 -
verificar "Year como texto" POST /api/books '{"title":"T","author":"A","year":"1938"}' 400 -
verificar "Campo desconhecido" POST /api/books '{"title":"T","author":"A","editora":"Record"}' 400 -
verificar "Content-Length invalido" POST /api/books '{"title":"T","author":"A"}' 400 - \
    -H "Content-Length: abc"

echo "--- ATUALIZACAO ---"
verificar "Substitui um livro" PUT /api/books/1 \
    '{"title":"Dom Casmurro","author":"Machado de Assis","year":1899,"available":false}' 200 -
verificar "Substitui livro inexistente" PUT /api/books/999 \
    '{"title":"T","author":"A"}' 404 -
verificar "Substitui sem os campos" PUT /api/books/1 '{}' 400 -
verificar "PUT na colecao" PUT /api/books '{"title":"T","author":"A"}' 405 Allow

echo "--- REMOCAO ---"
verificar "Remove um livro" DELETE /api/books/3 - 204 sem-corpo
verificar "Remove o mesmo livro de novo" DELETE /api/books/3 - 404 -
verificar "DELETE na colecao" DELETE /api/books - 405 Allow

echo "--- METODO NAO PERMITIDO ---"
verificar "POST no item" POST /api/books/1 '{"title":"T","author":"A"}' 405 Allow

echo "$PASSOU/$TOTAL passaram"

if [ "$PASSOU" -ne "$TOTAL" ]; then
    exit 1
fi
