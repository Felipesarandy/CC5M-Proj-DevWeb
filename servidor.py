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

# limite de 1 MiB para o corpo da requisicao
TAMANHO_MAXIMO_CORPO = 1048576


class LivroHandler(BaseHTTPRequestHandler):

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

    def enviar_json(self, status, dados):
        corpo = dict_para_json(dados)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()

        self.wfile.write(corpo)

    def erro_interno(self):
        # o traceback fica so no console, o cliente recebe mensagem generica
        traceback.print_exc()
        try:
            self.enviar_json(500, {"erro": "Erro interno do servidor."})
        except Exception:
            self.close_connection = True

    def ler_corpo(self):
        bruto = self.headers.get("Content-Length")

        if bruto is None:
            self.close_connection = True
            return None, "Header Content-Length ausente."

        try:
            tamanho = int(bruto)
        except ValueError:
            self.close_connection = True
            return None, "Header Content-Length inválido: era esperado um número inteiro."

        if tamanho < 0:
            # rfile.read(-1) leria ate o fim do socket e travaria o servidor, que e single-thread
            self.close_connection = True
            return None, "Header Content-Length não pode ser negativo."

        if tamanho > TAMANHO_MAXIMO_CORPO:
            self.close_connection = True
            return None, "Corpo da requisição maior que o limite de %d bytes." % TAMANHO_MAXIMO_CORPO

        return self.rfile.read(tamanho), None

    def do_GET(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.enviar_json(200, listar_livros())
                return

            if rota == "item":
                livro = buscar_livro(livro_id)

                if livro is None:
                    self.enviar_json(404, {"erro": "Livro não encontrado."})
                    return

                self.enviar_json(200, livro)
                return

            self.enviar_json(404, {"erro": "Rota não encontrada."})

        except Exception:
            self.erro_interno()

    def do_POST(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota != "colecao":
                self.enviar_json(404, {"erro": "Rota não encontrada."})
                return

            corpo, erro = self.ler_corpo()

            if erro:
                self.enviar_json(400, {"erro": erro})
                return

            dados, erro = json_para_dict(corpo)

            if erro:
                self.enviar_json(400, {"erro": erro})
                return

            erros = validar_livro(dados)

            if erros:
                self.enviar_json(400, {"erros": erros})
                return

            livro = criar_livro(dados)

            self.enviar_json(201, livro)

        except Exception:
            self.erro_interno()

    def do_PUT(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota != "item":
                self.enviar_json(404, {"erro": "Rota não encontrada."})
                return

            corpo, erro = self.ler_corpo()

            if erro:
                self.enviar_json(400, {"erro": erro})
                return

            dados, erro = json_para_dict(corpo)

            if erro:
                self.enviar_json(400, {"erro": erro})
                return

            erros = validar_livro(dados)

            if erros:
                self.enviar_json(400, {"erros": erros})
                return

            if buscar_livro(livro_id) is None:
                self.enviar_json(404, {"erro": "Livro não encontrado."})
                return

            self.enviar_json(200, atualizar_livro(livro_id, dados))

        except Exception:
            self.erro_interno()

    def do_DELETE(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota != "item":
                self.enviar_json(404, {"erro": "Rota não encontrada."})
                return

            if not remover_livro(livro_id):
                self.enviar_json(404, {"erro": "Livro não encontrado."})
                return

            self.send_response(204)
            self.end_headers()

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
    print("GET    /livros")
    print("GET    /livros/{id}")
    print("POST   /livros")
    print("PUT    /livros/{id}")
    print("DELETE /livros/{id}")
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
