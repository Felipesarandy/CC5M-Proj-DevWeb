from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
# mostrar erros detalhados no terminal
import traceback

from livros_dados import (
    listar_livros,
    buscar_livro,
    criar_livro,
    atualizar_livro,
    remover_livro,
    validar_livro,
    json_para_dict,
    dict_para_json,
    carregar_dados_exemplo
)

HOST = "localhost"
PORT = 8000


class LivroHandler(BaseHTTPRequestHandler):

    server_version = "CatalogoLivros/1.0"
    sys_version = ""

    MENSAGEM_ID_INVALIDO = "Identificador de livro inválido: deve ser um número inteiro."

    # quais métodos HTTP podem ser utilizados em cada tipo de rota
    METODOS_POR_ROTA = {
        "colecao": ("GET", "POST"),
        "item": ("GET", "PUT", "DELETE"),
    }

    # usadas quando quem dispara o erro e a stdlib, antes de chegar num do_*
    MENSAGENS_PADRAO = {
        400: "Requisição malformada.",
        501: "Método não implementado por este servidor.",
        505: "Versão do HTTP não suportada.",
    }

    def identificar_rota(self):
        caminho = urlparse(self.path).path

        if caminho != "/":
            caminho = caminho.rstrip("/")

        # /livros
        if caminho == "/livros":
            return "colecao", None

        # /livros/3
        partes = caminho.strip("/").split("/")

        if len(partes) == 2 and partes[0] == "livros":
            try:
                livro_id = int(partes[1])
                return "item", livro_id
            except ValueError:
                return None, None

        return None, None

    def enviar_json(self, status, dados, extras=None):
        """Responde com corpo JSON, o status e os headers extras informados."""
        corpo = dict_para_json(dados)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))

        if extras:
            for nome, valor in extras.items():
                self.send_header(nome, valor)

        self.end_headers()
        self.wfile.write(corpo)

    def enviar_erro(self, status, mensagem, detalhes=None, extras=None):
        """Responde um erro no formato único da API."""
        corpo = {"erro": mensagem}

        if detalhes:
            corpo["detalhes"] = detalhes

        self.enviar_json(status, corpo, extras)

    def metodo_nao_permitido(self, rota):
        """Responde 405 anunciando no header Allow os métodos aceitos na rota."""
        self.enviar_erro(
            405,
            "Método %s não permitido nesta rota." % self.command,
            extras={"Allow": ", ".join(self.METODOS_POR_ROTA[rota])}
        )

    def erro_interno(self):
        """Responde 500 e deixa o traceback apenas no console."""
        traceback.print_exc()
        try:
            self.enviar_erro(500, "Erro interno do servidor.")
        except Exception:
            pass

    def send_error(self, code, message=None, explain=None):
        """Faz os erros levantados pela stdlib saírem em JSON, não em HTML."""
        try:
            codigo = int(code)
        except (TypeError, ValueError):
            codigo = 500

        mensagem = self.MENSAGENS_PADRAO.get(codigo, "Não foi possível processar a requisição.")

        # o texto da stdlib vem em ingles, entao vira detalhe e nao mensagem principal
        detalhes = [str(message)] if message else []

        self.enviar_erro(codigo, mensagem, detalhes)

    def identificar_rota(self):
        """Classifica o caminho pedido em colecao, item, invalida ou desconhecida."""
        caminho = urlparse(self.path).path

        if caminho != "/":
            caminho = caminho.rstrip("/")

        if caminho == "/api/books":
            return "colecao", None

        partes = caminho.strip("/").split("/")

        if len(partes) == 3 and partes[0] == "api" and partes[1] == "books":
            try:
                return "item", int(partes[2])
            except ValueError:
                # o recurso existe na API, o id e que veio errado
                return "invalida", None

        return None, None

    def ler_corpo(self):
        """Lê o corpo JSON da requisição e devolve (dados, erro)."""
        bruto = self.headers.get("Content-Length")

        if bruto is None:
            return None, "Header Content-Length ausente."

        try:
            tamanho = int(bruto)
        except ValueError:
            return None, "Header Content-Length inválido: era esperado um número inteiro."

        if tamanho < 0:
            # rfile.read(-1) leria ate o fim do socket e travaria o servidor, que e single-thread
            return None, "Header Content-Length não pode ser negativo."

        dados, erro = json_para_dict(self.rfile.read(tamanho))

        if erro:
            return None, erro

        if not isinstance(dados, dict):
            return None, "O corpo da requisição deve ser um objeto JSON."

        return dados, None

    def do_GET(self):
        """Lista a coleção de livros ou devolve um livro pelo id."""
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.enviar_json(200, listar_livros())
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "item":
                self.enviar_erro(404, "Rota não encontrada.")
                return

            livro = buscar_livro(livro_id)

            if livro is None:
                self.enviar_erro(404, "Livro não encontrado.")
                return

            self.enviar_json(200, livro)

        except Exception:
            self.erro_interno()

    def do_POST(self):
        """Cria um livro novo na coleção."""
        try:
            rota, _ = self.identificar_rota()

            if rota == "item":
                self.metodo_nao_permitido("item")
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "colecao":
                self.enviar_erro(404, "Rota não encontrada.")
                return

            dados, erro = self.ler_corpo()

            if erro:
                self.enviar_erro(400, erro)
                return

            erros = validar_livro(dados)

            if erros:
                self.enviar_erro(400, "Dados do livro inválidos.", erros)
                return

            livro = criar_livro(dados)

            self.enviar_json(
                201,
                livro,
                extras={"Location": "/api/books/%d" % livro["id"]}
            )

        except Exception:
            self.erro_interno()

    def do_PUT(self):
        """Substitui por inteiro um livro existente."""
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.metodo_nao_permitido("colecao")
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "item":
                self.enviar_erro(404, "Rota não encontrada.")
                return

            dados, erro = self.ler_corpo()

            if erro:
                self.enviar_erro(400, erro)
                return

            erros = validar_livro(dados)

            if erros:
                self.enviar_erro(400, "Dados do livro inválidos.", erros)
                return

            if buscar_livro(livro_id) is None:
                self.enviar_erro(404, "Livro não encontrado.")
                return

            self.enviar_json(200, atualizar_livro(livro_id, dados))

        except Exception:
            self.erro_interno()

    def do_DELETE(self):
        """Remove um livro do catálogo."""
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.metodo_nao_permitido("colecao")
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "item":
                self.enviar_erro(404, "Rota não encontrada.")
                return

            if not remover_livro(livro_id):
                self.enviar_erro(404, "Livro não encontrado.")
                return

            self.send_response(204)
            self.end_headers()

        except Exception:
            self.erro_interno()


def iniciar_servidor():
    """Carrega os dados de exemplo e sobe o servidor HTTP."""
    carregar_dados_exemplo()

    servidor = HTTPServer(
        (HOST, PORT),
        LivroHandler
    )

    print("=" * 50)
    print("API de Livros iniciada")
    print(f"Servidor: http://{HOST}:{PORT}")
    print("GET     /api/books")
    print("GET     /api/books/{id}")
    print("POST    /api/books")
    print("PUT     /api/books/{id}")
    print("DELETE  /api/books/{id}")
    print("=" * 50)
    print("Pressione CTRL+C para encerrar.")

    try:
        servidor.serve_forever()

    except KeyboardInterrupt:
        print("\nServidor encerrado.")

    finally:
        servidor.server_close()


if __name__ == "__main__":
    iniciar_servidor()
