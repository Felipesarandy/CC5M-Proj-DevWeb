import json

_livros = {}
_proximo_id = 1

# Campos que todo livro precisa ter no momento da criação.
CAMPOS_OBRIGATORIOS = ("title", "author")
# Campos aceitos (qualquer coisa fora disso é recusada).
CAMPOS_PERMITIDOS = ("title", "author", "year", "available")


def listar_livros():
    """Devolve todos os livros do catálogo em uma lista."""
    return list(_livros.values())


def buscar_livro(livro_id):
    """Devolve o livro do id informado, ou None se ele não existir."""
    return _livros.get(livro_id)


def criar_livro(dados):
    """Cria um livro com um id novo e devolve o registro criado."""
    global _proximo_id
    livro = {
        "id": _proximo_id,
        "title": dados["title"],
        "author": dados["author"],
        "year": dados.get("year"),
        "available": dados.get("available", True),
    }
    _livros[_proximo_id] = livro
    _proximo_id += 1
    return livro


def atualizar_livro(livro_id, dados):
    """Substitui por inteiro o livro do id informado e devolve o resultado."""
    livro = {
        "id": livro_id,  # id fixo
        "title": dados["title"],
        "author": dados["author"],
        "year": dados.get("year"),
        "available": dados.get("available", True),
    }
    _livros[livro_id] = livro
    return livro


def remover_livro(livro_id):
    """Remove o livro do id informado e diz se ele existia."""
    if livro_id in _livros:
        del _livros[livro_id]
        return True
    return False


def validar_livro(dados):
    """Devolve a lista de erros dos dados de um livro, vazia se estiverem ok."""
    erros = []

    for campo in CAMPOS_OBRIGATORIOS:
        valor = dados.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            erros.append(f"O campo '{campo}' é obrigatório e deve ser um texto não vazio.")

    # isinstance(True, int) é True em Python, então o bool precisa ser barrado antes
    if "year" in dados and dados["year"] is not None:
        if isinstance(dados["year"], bool) or not isinstance(dados["year"], int):
            erros.append("O campo 'year' deve ser um número inteiro.")

    if "available" in dados and not isinstance(dados["available"], bool):
        erros.append("O campo 'available' deve ser true ou false.")

    desconhecidos = [c for c in dados if c not in CAMPOS_PERMITIDOS]
    if desconhecidos:
        erros.append(f"Campos não reconhecidos: {', '.join(desconhecidos)}.")

    return erros


def json_para_dict(corpo_bytes):
    """Converte os bytes do corpo em objeto Python e devolve (dados, erro)."""
    if not corpo_bytes:
        return None, "Corpo da requisição vazio: era esperado um JSON."
    try:
        return json.loads(corpo_bytes.decode("utf-8")), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "JSON malformado no corpo da requisição."


def dict_para_json(dados):
    """Converte um objeto Python em bytes JSON em UTF-8, com acento de verdade."""
    return json.dumps(dados, ensure_ascii=False, indent=2).encode("utf-8")


def carregar_dados_exemplo():
    """Popula o catálogo com três livros para a API não subir vazia."""
    exemplos = [
        {"title": "Dom Casmurro", "author": "Machado de Assis", "year": 1899, "available": True},
        {"title": "Grande Sertão: Veredas", "author": "João Guimarães Rosa", "year": 1956, "available": True},
        {"title": "Capitães da Areia", "author": "Jorge Amado", "year": 1937, "available": False},
    ]
    for dados in exemplos:
        criar_livro(dados)


# Teste rápido do módulo isolado (rode: python livros_dados.py)

if __name__ == "__main__":
    carregar_dados_exemplo()

    print("Todos os livros:")
    print(dict_para_json(listar_livros()).decode("utf-8"))

    print("\nBuscar id=2:", buscar_livro(2))
    print("Buscar id=99:", buscar_livro(99))

    novo = criar_livro({"title": "Vidas Secas", "author": "Graciliano Ramos", "year": 1938})
    print("\nCriado:", novo)

    print("\nValidação de dados ruins:", validar_livro({"title": "", "year": "1899"}))

    dados, erro = json_para_dict(b'{"title": "Teste"')
    print("JSON malformado ->", erro)

    print("\nRemover id=1:", remover_livro(1))
    print("Remover id=1 de novo:", remover_livro(1))
