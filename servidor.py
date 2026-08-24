from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
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

        # /api/books
        if caminho == "/api/books":
            return "colecao", None

        # /api/books/3
        partes = caminho.strip("/").split("/")

        if len(partes) == 3 and partes[0] == "api" and partes[1] == "books":
            try:
                return "item", int(partes[2])
            except ValueError:
                # o recurso existe na API, o id e que veio errado
                return "invalida", None

        return None, None

    def enviar_json(self, status, dados, extras=None):
        corpo = dict_para_json(dados)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))

        if extras:
            for nome, valor in extras.items():
                self.send_header(nome, valor)

        self.end_headers()
        self.wfile.write(corpo)

    def enviar_sem_corpo(self, status, extras=None):
        self.send_response(status)

        if extras:
            for nome, valor in extras.items():
                self.send_header(nome, valor)

        self.end_headers()

    def send_error(self, code, message=None, explain=None):
        # erros levantados pela propria stdlib (verbo desconhecido, linha de pedido
        # invalida, header grande demais) sairiam em HTML e quebrariam o contrato JSON
        try:
            codigo = int(code)
        except (TypeError, ValueError):
            codigo = 500

        mensagem = self.MENSAGENS_PADRAO.get(codigo, "Não foi possível processar a requisição.")

        # o texto da stdlib vem em ingles, entao vira detalhe e nao mensagem principal
        detalhes = [str(message)] if message else []

        if codigo < 200 or codigo in (204, 205, 304):
            self.enviar_sem_corpo(codigo)
            return

        self.enviar_erro(codigo, mensagem, detalhes)

    def enviar_erro(self, status, mensagem, detalhes=None, extras=None):
        envelope = {
            "erro": {
                "status": status,
                "mensagem": mensagem,
                "detalhes": detalhes if detalhes else [],
            }
        }
        self.enviar_json(status, envelope, extras)

    def erro_interno(self):
        # o traceback fica so no console, o cliente recebe mensagem generica
        traceback.print_exc()
        try:
            self.enviar_erro(500, "Erro interno do servidor.")
        except Exception:
            pass

    def ler_corpo(self):
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

        return self.rfile.read(tamanho), None

    def metodo_nao_permitido(self, rota):
        permitidos = ", ".join(self.METODOS_POR_ROTA[rota])
        self.enviar_erro(
            405,
            "Método %s não permitido nesta rota." % self.command,
            extras={"Allow": permitidos}
        )

    def rota_nao_encontrada(self):
        self.enviar_erro(404, "Rota não encontrada.")

    def obter_payload(self):
        # devolve (dados, mensagem_do_erro, detalhes)
        corpo, erro = self.ler_corpo()
        if erro:
            return None, erro, []

        dados, erro = json_para_dict(corpo)
        if erro:
            return None, erro, []

        if not isinstance(dados, dict):
            return None, "O corpo da requisição deve ser um objeto JSON.", []

        erros = validar_livro(dados)
        if erros:
            return None, "Dados do livro inválidos.", erros

        return dados, None, None

    def do_GET(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.enviar_json(200, listar_livros())
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota == "item":
                livro = buscar_livro(livro_id)

                if livro is None:
                    self.enviar_erro(404, "Livro não encontrado.")
                    return

                self.enviar_json(200, livro)
                return

            self.enviar_erro(404, "Rota não encontrada.")

        except Exception:
            self.erro_interno()

    def do_POST(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "item":
                self.metodo_nao_permitido("item")
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "colecao":
                self.rota_nao_encontrada()
                return

            dados, mensagem, detalhes = self.obter_payload()

            if mensagem:
                self.enviar_erro(400, mensagem, detalhes)
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
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.metodo_nao_permitido("colecao")
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "item":
                self.rota_nao_encontrada()
                return

            # o corpo e lido antes de checar a existencia para nao deixar bytes na conexao
            dados, mensagem, detalhes = self.obter_payload()

            if mensagem:
                self.enviar_erro(400, mensagem, detalhes)
                return

            if buscar_livro(livro_id) is None:
                self.enviar_erro(404, "Livro não encontrado.")
                return

            self.enviar_json(200, atualizar_livro(livro_id, dados))

        except Exception:
            self.erro_interno()

    def do_DELETE(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.metodo_nao_permitido("colecao")
                return

            if rota == "invalida":
                self.enviar_erro(400, self.MENSAGEM_ID_INVALIDO)
                return

            if rota != "item":
                self.rota_nao_encontrada()
                return

            if not remover_livro(livro_id):
                self.enviar_erro(404, "Livro não encontrado.")
                return

            self.enviar_sem_corpo(204)

        except Exception:
            self.erro_interno()


def iniciar_servidor():

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
