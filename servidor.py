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

# limite de 1 MiB para o corpo da requisicao
TAMANHO_MAXIMO_CORPO = 1048576


class LivroHandler(BaseHTTPRequestHandler):

    server_version = "CatalogoLivros/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # quais métodos HTTP podem ser utilizados em cada tipo de rota
    METODOS_POR_ROTA = {
        "colecao": ("GET", "HEAD", "POST", "OPTIONS"),
        "item": ("GET", "HEAD", "PUT", "DELETE", "OPTIONS"),
    }

    # usadas quando quem dispara o erro e a stdlib, antes de chegar num do_*
    MENSAGENS_PADRAO = {
        400: "Requisição malformada.",
        414: "URI da requisição longa demais.",
        431: "Cabeçalhos da requisição grandes demais.",
        501: "Método não implementado por este servidor.",
        505: "Versão do HTTP não suportada.",
    }

    # descobre qual recurso está tentando ser acessado
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

    # converte um dicionário, lista Python para JSON e depois bytes
    def enviar_json(self, status, dados, extras=None):
        corpo = dict_para_json(dados)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))

        if extras:
            for nome, valor in extras.items():
                self.send_header(nome, valor)

        self.end_headers()

        # o HEAD reaproveita o do_GET e precisa dos mesmos headers, mas sem corpo
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def enviar_sem_corpo(self, status, extras=None):
        self.send_response(status)

        if extras:
            for nome, valor in extras.items():
                self.send_header(nome, valor)

        self.end_headers()

    def version_string(self):
        # sem isso o header Server sairia com um espaco sobrando no fim
        return self.server_version

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

        # sao erros de protocolo, e o corpo pendente da requisicao nunca foi lido
        self.close_connection = True

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

    def descartar_corpo(self):
        # sem consumir o corpo, o proximo pedido da mesma conexao HTTP/1.1 sairia desalinhado
        bruto = self.headers.get("Content-Length")

        if bruto is None:
            return

        try:
            tamanho = int(bruto)
        except ValueError:
            self.close_connection = True
            return

        if tamanho < 0 or tamanho > TAMANHO_MAXIMO_CORPO:
            self.close_connection = True
            return

        self.rfile.read(tamanho)

    def content_type_valido(self):
        cabecalho = self.headers.get("Content-Type", "")
        return cabecalho.split(";")[0].strip().lower() == "application/json"

    def metodo_nao_permitido(self, rota):
        self.descartar_corpo()
        permitidos = ", ".join(self.METODOS_POR_ROTA[rota])
        self.enviar_erro(
            405,
            "Método %s não permitido nesta rota." % self.command,
            extras={"Allow": permitidos}
        )

    def rota_nao_encontrada(self):
        self.descartar_corpo()
        self.enviar_erro(404, "Rota não encontrada.")

    def obter_payload(self):
        # devolve (dados, status_do_erro, mensagem, detalhes)
        if not self.content_type_valido():
            self.descartar_corpo()
            return None, 415, "Content-Type deve ser application/json.", []

        corpo, erro = self.ler_corpo()
        if erro:
            return None, 400, erro, []

        dados, erro = json_para_dict(corpo)
        if erro:
            return None, 400, erro, []

        if not isinstance(dados, dict):
            return None, 400, "O corpo da requisição deve ser um objeto JSON.", []

        erros = validar_livro(dados)
        if erros:
            return None, 422, "Dados do livro inválidos.", erros

        return dados, None, None, None

    def do_GET(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.enviar_json(200, listar_livros())
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

    def do_HEAD(self):
        # mesmos status e headers do GET, que ja carrega a propria rede de seguranca de 500
        self.do_GET()

    def do_POST(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "item":
                self.metodo_nao_permitido("item")
                return

            if rota != "colecao":
                self.rota_nao_encontrada()
                return

            dados, status, mensagem, detalhes = self.obter_payload()

            if status:
                self.enviar_erro(status, mensagem, detalhes)
                return

            livro = criar_livro(dados)

            self.enviar_json(
                201,
                livro,
                extras={"Location": "/livros/%d" % livro["id"]}
            )

        except Exception:
            self.erro_interno()

    def do_PUT(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota == "colecao":
                self.metodo_nao_permitido("colecao")
                return

            if rota != "item":
                self.rota_nao_encontrada()
                return

            # o corpo e lido antes de checar a existencia para nao deixar bytes na conexao
            dados, status, mensagem, detalhes = self.obter_payload()

            if status:
                self.enviar_erro(status, mensagem, detalhes)
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

            if rota != "item":
                self.rota_nao_encontrada()
                return

            if not remover_livro(livro_id):
                self.enviar_erro(404, "Livro não encontrado.")
                return

            self.enviar_sem_corpo(204)

        except Exception:
            self.erro_interno()

    def do_PATCH(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota is None:
                self.rota_nao_encontrada()
                return

            # atualizacao parcial esta fora do escopo, entao a rota so anuncia o que aceita
            self.metodo_nao_permitido(rota)

        except Exception:
            self.erro_interno()

    def do_OPTIONS(self):
        try:
            rota, livro_id = self.identificar_rota()

            if rota is None:
                self.rota_nao_encontrada()
                return

            self.enviar_sem_corpo(
                204,
                extras={"Allow": ", ".join(self.METODOS_POR_ROTA[rota])}
            )

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
    print("GET     /livros")
    print("GET     /livros/{id}")
    print("POST    /livros")
    print("PUT     /livros/{id}")
    print("DELETE  /livros/{id}")
    print("HEAD    /livros e /livros/{id}")
    print("OPTIONS /livros e /livros/{id}")
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
