#!/usr/bin/env bash
# Arquivo bash de testes com curl da API de catalogo de livros.
#
#   Terminal 1:  python servidor.py
#   Terminal 2:  bash testes.sh

BASE="http://localhost:8000"
JSON="Content-Type: application/json"

# Define variaveis temporarias para armazenar o corpo e os cabecalhos

CORPO=$(mktemp)
CABECALHOS=$(mktemp)
trap 'rm -f "$CORPO" "$CABECALHOS"' EXIT

# Variaveis globais de contagem.

TOTAL=0
PASSOU=0

# Função principal que executa o teste das requisições.

verificar() {
    # Declaração das variaveis "$posição" para os parâmetros da função.
    descricao="$1"
    metodo="$2"
    uri="$3"
    dados="$4"
    esperado="$5"
    exigido="$6"
    shift 6

    # Incrementa o contador.
    TOTAL=$((TOTAL + 1))

    # Prepara os argumentos do curl de acordo com a presença ou ausência de dados.
    # Caso for dados com "-", não envia o corpo , DELETE ou GET.
    # Se tiver é POST / PUT (corpo em JSON) definido no parametro $dados.
    if [ "$dados" = "-" ]; then
        set -- -X "$metodo" "$BASE$uri" "$@" 
    else
        set -- -X "$metodo" "$BASE$uri" -H "$JSON" -d "$dados" "$@"
    fi

    # Executa o curl com os argumentos preparados, armazenando o corpo e os cabecalhos em arquivos temporarios definidos pelo (mktemp).
    resposta=$(curl -s -o "$CORPO" -D "$CABECALHOS" -w '%{http_code}|%{size_download}' \
        --max-time 6 "$@")

    obtido=${resposta%%|*} # Codigo HTTP obtido
    baixado=${resposta##*|} # Tamanho do corpo baixado em bytes
    ok="sim"
    extra=""

    # Compara o codigo HTTP obtido com o esperado, se forem diferentes, define a variavel "ok" como "nao".
    if [ "$obtido" != "$esperado" ]; then
        ok="nao"
    fi

    # Verifica o valor de "exigido", define a variavel como "nao" se o header exigido estiver ausente, ou define a variavel "extra" com o valor do header.

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

# Verifica se o servidor esta rodando, se não estiver imprime uma mensagem de erro.

if ! curl -s -o /dev/null --max-time 5 "$BASE/api/books"; then
    echo "Servidor nao respondeu em $BASE. Rode 'python servidor.py' antes." >&2
    exit 1
fi

# Print de inicio da execução dos testes.

echo "Suite de testes - API de catalogo de livros"
echo "Base: $BASE"
echo

# Teste de GET

echo "--- LEITURA ---"
verificar "Lista a colecao" GET /api/books - 200 -
verificar "Consulta um livro" GET /api/books/1 - 200 -
verificar "Livro inexistente" GET /api/books/999 - 404 -
verificar "Id que nao e inteiro" GET /api/books/abc - 400 -
verificar "Rota inexistente" GET /rota-inexistente - 404 -

# Teste de POST

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

# Teste de PUT 

echo "--- ATUALIZACAO ---"
verificar "Substitui um livro" PUT /api/books/1 \
    '{"title":"Dom Casmurro","author":"Machado de Assis","year":1899,"available":false}' 200 -
verificar "Substitui livro inexistente" PUT /api/books/999 \
    '{"title":"T","author":"A"}' 404 -
verificar "Substitui sem os campos" PUT /api/books/1 '{}' 400 -
verificar "PUT na colecao" PUT /api/books '{"title":"T","author":"A"}' 405 Allow

# Teste de DELETE
echo "--- REMOCAO ---"
verificar "Remove um livro" DELETE /api/books/3 - 204 sem-corpo
verificar "Remove o mesmo livro de novo" DELETE /api/books/3 - 404 -
verificar "DELETE na colecao" DELETE /api/books - 405 Allow

# Print de testes de métodos não permitidos.. 

echo "--- METODO NAO PERMITIDO ---"
verificar "POST no item" POST /api/books/1 '{"title":"T","author":"A"}' 405 Allow

# Print de quantos testes passaram e quantos foram executados.
echo "$PASSOU/$TOTAL passaram"

# Condicional se algum teste falhou... 

if [ "$PASSOU" -ne "$TOTAL" ]; then
    exit 1
fi
