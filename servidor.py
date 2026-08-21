from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

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

    # ---------------------------------------------------------
    # ROTEAMENTO
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # RESPOSTA JSON
    # ---------------------------------------------------------
    def enviar_json(self, status, dados):
        corpo = dict_para_json(dados)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()

        self.wfile.write(corpo)

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------
    def do_GET(self):
        rota, livro_id = self.identificar_rota()

        if rota == "colecao":
            livros = listar_livros()
            self.enviar_json(200, livros)
            return

        if rota == "item":
            livro = buscar_livro(livro_id)

            if livro is None:
                self.enviar_json(
                    404,
                    {"erro": "Livro não encontrado."}
                )
                return

            self.enviar_json(200, livro)
            return

        self.enviar_json(
            404,
            {"erro": "Rota não encontrada."}
        )

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------
    def do_POST(self):
        rota, livro_id = self.identificar_rota()

        if rota != "colecao":
            self.enviar_json(
                404,
                {"erro": "Rota não encontrada."}
            )
            return

        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho)

        dados, erro = json_para_dict(corpo)

        if erro:
            self.enviar_json(
                400,
                {"erro": erro}
            )
            return

        erros = validar_livro(dados)

        if erros:
            self.enviar_json(
                400,
                {"erros": erros}
            )
            return

        livro = criar_livro(dados)

        self.enviar_json(
            201,
            livro
        )

    # ---------------------------------------------------------
    # PUT
    # ---------------------------------------------------------
    def do_PUT(self):
        rota, livro_id = self.identificar_rota()

        if rota != "item":
            self.enviar_json(
                404,
                {"erro": "Rota não encontrada."}
            )
            return

        livro_existente = buscar_livro(livro_id)

        if livro_existente is None:
            self.enviar_json(
                404,
                {"erro": "Livro não encontrado."}
            )
            return

        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho)

        dados, erro = json_para_dict(corpo)

        if erro:
            self.enviar_json(
                400,
                {"erro": erro}
            )
            return

        erros = validar_livro(dados)

        if erros:
            self.enviar_json(
                400,
                {"erros": erros}
            )
            return

        livro = atualizar_livro(livro_id, dados)

        self.enviar_json(
            200,
            livro
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------
    def do_DELETE(self):
        rota, livro_id = self.identificar_rota()

        if rota != "item":
            self.enviar_json(
                404,
                {"erro": "Rota não encontrada."}
            )
            return

        removido = remover_livro(livro_id)

        if not removido:
            self.enviar_json(
                404,
                {"erro": "Livro não encontrado."}
            )
            return

        self.send_response(204)
        self.end_headers()


# -------------------------------------------------------------
# INICIALIZAÇÃO DO SERVIDOR
# -------------------------------------------------------------
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