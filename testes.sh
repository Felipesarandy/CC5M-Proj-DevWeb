#!/usr/bin/env bash
# Suite de testes com curl da API de catalogo de livros.
# Precisa do servidor recem-iniciado, porque conta com os ids 1, 2 e 3
# criados por carregar_dados_exemplo() e com a ordem dos casos abaixo.
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

# verificar <descricao> <status esperado> <checagem extra> <argumentos do curl...>
# checagem extra aceita "-", "Location", "Allow" ou "sem-corpo"
verificar() {
    descricao="$1"
    esperado="$2"
    extra="$3"
    shift 3

    TOTAL=$((TOTAL + 1))

    resposta=$(curl -s -o "$CORPO" -D "$CABECALHOS" -w '%{http_code}|%{size_download}' --max-time 6 "$@")
    obtido=${resposta%%|*}
    baixado=${resposta##*|}

    ok="sim"
    detalhe=""

    if [ "$obtido" != "$esperado" ]; then
        ok="nao"
    fi

    case "$extra" in
        Location|Allow)
            valor=$(grep -i "^$extra:" "$CABECALHOS" | head -1 | tr -d '\r' | cut -d' ' -f2-)
            if [ -z "$valor" ]; then
                ok="nao"
                detalhe="$extra AUSENTE"
            else
                detalhe="$extra: $valor"
            fi
            ;;
        sem-corpo)
            if [ "$baixado" != "0" ]; then
                ok="nao"
                detalhe="corpo deveria estar vazio, veio $baixado bytes"
            else
                detalhe="corpo vazio"
            fi
            ;;
    esac

    if [ "$ok" = "sim" ]; then
        PASSOU=$((PASSOU + 1))
        resultado="OK"
    else
        resultado="FALHOU"
    fi

    printf '%-46s esperado %-3s obtido %-3s  %-7s %s\n' \
        "$descricao" "$esperado" "$obtido" "$resultado" "$detalhe"
}

if ! curl -s -o /dev/null --max-time 5 "$BASE/livros"; then
    echo "Servidor nao respondeu em $BASE. Rode 'python servidor.py' antes." >&2
    exit 1
fi

echo "Suite de testes - API de catalogo de livros"
echo "Base: $BASE"
echo

echo "LEITURA"
verificar "GET /livros" 200 - "$BASE/livros"
verificar "GET /livros/1" 200 - "$BASE/livros/1"
verificar "GET /livros/999" 404 - "$BASE/livros/999"
verificar "GET /livros/abc" 404 - "$BASE/livros/abc"
verificar "GET /rota-inexistente" 404 - "$BASE/rota-inexistente"
echo

echo "CRIACAO"
verificar "POST /livros valido" 201 Location \
    -X POST "$BASE/livros" -H "$JSON" \
    -d '{"titulo":"Vidas Secas","autor":"Graciliano Ramos","ano":1938}'
verificar "POST /livros Content-Type text/plain" 415 - \
    -X POST "$BASE/livros" -H "Content-Type: text/plain" \
    -d '{"titulo":"T","autor":"A"}'
verificar "POST /livros JSON malformado" 400 - \
    -X POST "$BASE/livros" -H "$JSON" -d '{"titulo":'
verificar "POST /livros corpo vazio" 400 - \
    -X POST "$BASE/livros" -H "$JSON" -d ''
verificar "POST /livros corpo [1,2]" 400 - \
    -X POST "$BASE/livros" -H "$JSON" -d '[1,2]'
verificar "POST /livros Content-Length abc" 400 - \
    -X POST "$BASE/livros" -H "$JSON" -H "Content-Length: abc" \
    -d '{"titulo":"T","autor":"A"}'
verificar "POST /livros titulo vazio" 422 - \
    -X POST "$BASE/livros" -H "$JSON" -d '{"titulo":"","autor":"Alguem"}'
verificar "POST /livros ano como texto" 422 - \
    -X POST "$BASE/livros" -H "$JSON" -d '{"titulo":"T","autor":"A","ano":"1938"}'
verificar "POST /livros campo desconhecido" 422 - \
    -X POST "$BASE/livros" -H "$JSON" -d '{"titulo":"T","autor":"A","editora":"Record"}'
verificar "POST /livros sem titulo" 422 - \
    -X POST "$BASE/livros" -H "$JSON" -d '{"autor":"Alguem"}'
echo

echo "ATUALIZACAO"
verificar "PUT /livros/1" 200 - \
    -X PUT "$BASE/livros/1" -H "$JSON" \
    -d '{"titulo":"Dom Casmurro","autor":"Machado de Assis","ano":1899}'
verificar "PUT /livros/999" 404 - \
    -X PUT "$BASE/livros/999" -H "$JSON" -d '{"titulo":"T","autor":"A"}'
verificar "PUT /livros/1 payload invalido" 422 - \
    -X PUT "$BASE/livros/1" -H "$JSON" -d '{"titulo":"","autor":""}'
verificar "PUT /livros (colecao)" 405 Allow \
    -X PUT "$BASE/livros" -H "$JSON" -d '{"titulo":"T","autor":"A"}'
echo

echo "REMOCAO"
verificar "DELETE /livros/3" 204 - -X DELETE "$BASE/livros/3"
verificar "DELETE /livros/3 repetido" 404 - -X DELETE "$BASE/livros/3"
verificar "DELETE /livros (colecao)" 405 Allow -X DELETE "$BASE/livros"
echo

echo "METODOS NAO PERMITIDOS E NEGOCIACAO"
verificar "POST /livros/1 (item)" 405 Allow \
    -X POST "$BASE/livros/1" -H "$JSON" -d '{"titulo":"T","autor":"A"}'
verificar "PATCH /livros/1" 405 Allow \
    -X PATCH "$BASE/livros/1" -H "$JSON" -d '{"titulo":"T"}'
verificar "OPTIONS /livros" 204 Allow -X OPTIONS "$BASE/livros"
verificar "HEAD /livros" 200 sem-corpo -I "$BASE/livros"
echo

echo "$PASSOU/$TOTAL passaram"

if [ "$PASSOU" -ne "$TOTAL" ]; then
    exit 1
fi
