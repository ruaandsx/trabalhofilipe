"""API Gateway do HelpDesk TI.

É a única porta de entrada (8000). Serve a tela e encaminha cada pedido ao serviço certo.
Não decide permissões nem lê o token: quem confere o JWT é cada serviço.
"""
import asyncio
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from app import config
from app.seguranca_http import CabecalhosDeSeguranca

log = logging.getLogger("gateway")
WEB = Path(__file__).parent / "web"

# Só estes cabeçalhos do pedido seguem para o serviço (o resto é descartado)
CABECALHOS_DO_PEDIDO = ("authorization", "content-type", "accept", "user-agent")
# Só estes cabeçalhos da resposta voltam para o navegador (os de segurança são do gateway)
CABECALHOS_DA_RESPOSTA = ("content-type", "www-authenticate", "retry-after")

# Só os testes mexem nisto (para simular os serviços sem rede)
TRANSPORTE: httpx.AsyncBaseTransport | None = None

app = FastAPI(title="HelpDesk TI · Gateway", version="3.0.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CabecalhosDeSeguranca)


def _cliente(timeout: float = config.TIMEOUT_SEGUNDOS) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=config.TIMEOUT_CONEXAO_SEGUNDOS), transport=TRANSPORTE)


@app.get("/saude", tags=["Saúde"])
async def saude():
    """Situação do gateway e de cada serviço."""
    async def consultar(nome: str, base: str):
        try:
            async with _cliente(config.TIMEOUT_SAUDE_SEGUNDOS) as http:
                r = await http.get(f"{base}/saude")
            return nome, "ok" if r.status_code == 200 else "com problemas"
        except httpx.HTTPError:
            return nome, "fora do ar"

    resultados = dict(await asyncio.gather(*(consultar(n, b) for n, b in config.SERVICOS.items())))
    geral = "ok" if all(v == "ok" for v in resultados.values()) else "degradado"
    return JSONResponse({"status": geral, "servicos": resultados}, status_code=200 if geral == "ok" else 503)


@app.get("/", include_in_schema=False)
def tela_inicial():
    return FileResponse(WEB / "index.html")


@app.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(WEB / "app.js", media_type="text/javascript")


@app.get("/estilo.css", include_in_schema=False)
def estilo():
    return FileResponse(WEB / "estilo.css", media_type="text/css")


@app.api_route("/{caminho:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"], include_in_schema=False)
async def encaminhar(caminho: str, request: Request) -> Response:
    base = config.ROTAS.get(caminho.split("/", 1)[0])
    if base is None:
        return JSONResponse(status_code=404, content={"detail": "Rota não encontrada."})

    cabecalhos = {k: v for k, v in request.headers.items() if k.lower() in CABECALHOS_DO_PEDIDO}
    # Informa o endereço de quem chamou (o limite de tentativas de login usa isso)
    cabecalhos["x-forwarded-for"] = request.client.host if request.client else "-"
    try:
        async with _cliente() as http:
            r = await http.request(request.method, f"{base}/{caminho}", params=request.query_params,
                                   content=await request.body(), headers=cabecalhos)
    except httpx.TimeoutException:
        log.warning("Timeout em %s", caminho.split("/", 1)[0])
        return JSONResponse(status_code=504, content={"detail": "O serviço demorou demais para responder."},
                            headers={"Retry-After": "5"})
    except httpx.HTTPError:
        log.warning("Serviço fora do ar: %s", caminho.split("/", 1)[0])
        return JSONResponse(status_code=503, content={"detail": "O serviço está indisponível no momento. Tente novamente em instantes."},
                            headers={"Retry-After": "5"})

    saida = {k: v for k, v in r.headers.items() if k.lower() in CABECALHOS_DA_RESPOSTA}
    return Response(content=r.content, status_code=r.status_code, headers=saida)
