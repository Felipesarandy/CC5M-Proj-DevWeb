import json

# ---------------------------------------------------------------------------
# "Banco de dados" em memória
# ---------------------------------------------------------------------------
# Usamos um dicionário {id: livro} porque busca por id fica O(1),
# e um contador para gerar ids únicos e crescentes.

_livros = {}
_proximo_id = 1

# Campos que todo livro precisa ter no momento da criação.
CAMPOS_OBRIGATORIOS = ("titulo", "autor")
# Campos aceitos (qualquer coisa fora disso é ignorada/recusada).
CAMPOS_PERMITIDOS = ("titulo", "autor", "ano", "isbn")


# ---------------------------------------------------------------------------
# Operações CRUD
# ---------------------------------------------------------------------------

def listar_livros():
    
    return list(_livros.values())


def buscar_livro(livro_id):
    
    return _livros.get(livro_id)


def criar_livro(dados):
    
    global _proximo_id
    livro = {
        "id": _proximo_id,
        "titulo": dados["titulo"],
        "autor": dados["autor"],
        "ano": dados.get("ano"),
        "isbn": dados.get("isbn"),
    }
    _livros[_proximo_id] = livro
    _proximo_id += 1
    return livro


def atualizar_livro(livro_id, dados):
    
    if livro_id not in _livros:
        return None
    livro = {
        "id": livro_id,  # o id nunca muda
        "titulo": dados["titulo"],
        "autor": dados["autor"],
        "ano": dados.get("ano"),
        "isbn": dados.get("isbn"),
    }
    _livros[livro_id] = livro
    return livro


def remover_livro(livro_id):
    
    if livro_id in _livros:
        del _livros[livro_id]
        return True
    return False


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def validar_livro(dados):
    
    erros = []

    if not isinstance(dados, dict):
        return ["O corpo da requisição deve ser um objeto JSON."]

    for campo in CAMPOS_OBRIGATORIOS:
        valor = dados.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            erros.append(f"O campo '{campo}' é obrigatório e deve ser um texto não vazio.")

    if "ano" in dados and dados["ano"] is not None and not isinstance(dados["ano"], int):
        erros.append("O campo 'ano' deve ser um número inteiro.")

    if "isbn" in dados and dados["isbn"] is not None and not isinstance(dados["isbn"], str):
        erros.append("O campo 'isbn' deve ser um texto.")

    desconhecidos = [c for c in dados if c not in CAMPOS_PERMITIDOS]
    if desconhecidos:
        erros.append(f"Campos não reconhecidos: {', '.join(desconhecidos)}.")

    return erros


# ---------------------------------------------------------------------------
# Conversão JSON <-> Python
# ---------------------------------------------------------------------------

def json_para_dict(corpo_bytes):
    
    if not corpo_bytes:
        return None, "Corpo da requisição vazio: era esperado um JSON."
    try:
        return json.loads(corpo_bytes.decode("utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "JSON malformado no corpo da requisição."


def dict_para_json(dados):
    
    return json.dumps(dados, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# Dados iniciais (opcional, ajuda na demonstração de sexta)
# ---------------------------------------------------------------------------

def carregar_dados_exemplo():
    
    exemplos = [
        {"titulo": "Dom Casmurro", "autor": "Machado de Assis", "ano": 1899, "isbn": "978-8535910663"},
        {"titulo": "Grande Sertão: Veredas", "autor": "João Guimarães Rosa", "ano": 1956, "isbn": "978-8535928280"},
        {"titulo": "Capitães da Areia", "autor": "Jorge Amado", "ano": 1937, "isbn": "978-8535914061"},
    ]
    for dados in exemplos:
        criar_livro(dados)


# ---------------------------------------------------------------------------
# Teste rápido do módulo isolado (rode: python livros_dados.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    carregar_dados_exemplo()

    print("Todos os livros:")
    print(dict_para_json(listar_livros()).decode("utf-8"))

    print("\nBuscar id=2:", buscar_livro(2))
    print("Buscar id=99:", buscar_livro(99))

    novo = criar_livro({"titulo": "Vidas Secas", "autor": "Graciliano Ramos", "ano": 1938})
    print("\nCriado:", novo)

    print("\nValidação de dados ruins:", validar_livro({"titulo": "", "ano": "1899"}))

    dados, erro = json_para_dict(b'{"titulo": "Teste"')
    print("JSON malformado ->", erro)

    print("\nRemover id=1:", remover_livro(1))
    print("Remover id=1 de novo:", remover_livro(1))