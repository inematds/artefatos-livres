#!/usr/bin/env python3
"""artefatos-livres — suas páginas por link, sem depender de nenhuma IA nem de nuvem de terceiros.

O que faz (só biblioteca padrão do Python 3.9+):
  novo      cria uma página a partir do modelo (paginas/<nome>/index.html)
  publicar  congela a versão: o link fixo mostra a última, /v/N/ guarda cada uma
  versoes   lista as versões publicadas
  servir    sobe o servidor: páginas, dados compartilhados, comentários e IA opcional
  link      imprime o link para compartilhar (com a chave, se a página for privada)
  exportar  copia página + dados (JSON e CSV) para uma pasta sua — a porta de saída

Qualquer IA (Claude, Codex, Gemini, um modelo local) ou você mesmo escreve o index.html.
O contrato da página está em CONTRATO.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import secrets
import shlex
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

VERSAO = "1.0.0"
RAIZ_KIT = Path(__file__).resolve().parent
NOME_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
COLECAO_OK = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
LIMITE_CORPO = 256 * 1024  # 256 KB por requisição
LIMITE_DOC = 64 * 1024
TIPOS = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json", ".svg": "image/svg+xml",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8", ".csv": "text/csv; charset=utf-8",
}


# ---------------------------------------------------------------- pastas
class Area:
    """Onde ficam as páginas (fonte), o site publicado e os dados."""

    def __init__(self, base: Path):
        self.base = Path(base).resolve()
        self.paginas = self.base / "paginas"
        self.site = self.base / "site"
        self.dados = self.base / "dados"

    def preparar(self):
        for p in (self.paginas, self.site, self.dados):
            p.mkdir(parents=True, exist_ok=True)

    def conf(self, nome: str) -> dict:
        arq = self.paginas / nome / "pagina.json"
        if not arq.exists():
            raise SystemExit(f"página '{nome}' não existe (crie com: novo {nome})")
        return json.loads(arq.read_text(encoding="utf-8"))

    def salvar_conf(self, nome: str, conf: dict):
        (self.paginas / nome / "pagina.json").write_text(
            json.dumps(conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def checar_nome(nome: str) -> str:
    if not NOME_OK.match(nome or ""):
        raise SystemExit("nome inválido: use minúsculas, números e hífen (ex.: tarefas-da-semana)")
    return nome


# ---------------------------------------------------------------- comandos
def cmd_novo(area: Area, nome: str, titulo: str, publica: bool, modelo: str) -> Path:
    checar_nome(nome)
    area.preparar()
    pasta = area.paginas / nome
    if pasta.exists():
        raise SystemExit(f"já existe: {pasta}")
    origem = RAIZ_KIT / "modelos" / modelo
    if not (origem / "index.html").exists():
        raise SystemExit(f"modelo '{modelo}' não encontrado em {RAIZ_KIT / 'modelos'}")
    shutil.copytree(origem, pasta)
    idx = pasta / "index.html"
    idx.write_text(idx.read_text(encoding="utf-8").replace("{{TITULO}}", html.escape(titulo)),
                   encoding="utf-8")
    area.salvar_conf(nome, {
        "titulo": titulo,
        "privada": not publica,
        "chave": secrets.token_urlsafe(12),
        "criada": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cor": "#FACC15",
    })
    return pasta


def _manifest(nome: str, conf: dict) -> dict:
    return {
        "name": conf["titulo"], "short_name": conf["titulo"][:24],
        "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": "#0c0c10", "theme_color": conf.get("cor", "#FACC15"),
        "icons": [{"src": "icone.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    }


def _icone(conf: dict) -> str:
    letra = html.escape((conf["titulo"].strip() or "A")[0].upper())
    cor = conf.get("cor", "#FACC15")
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'>"
            f"<rect width='512' height='512' rx='96' fill='#0c0c10'/>"
            f"<text x='256' y='340' font-size='280' text-anchor='middle' font-family='sans-serif' "
            f"font-weight='700' fill='{cor}'>{letra}</text></svg>")


def _sw(versao: int) -> str:
    # rede primeiro (a versão nova aparece assim que for publicada); cache só se cair a rede
    return (RAIZ_KIT / "nucleo" / "sw.js").read_text(encoding="utf-8").replace("{{VERSAO}}", str(versao))


def _injetar(html_txt: str) -> str:
    """Põe manifest, ícone e livre.js no <head> se a página ainda não tiver."""
    extra = []
    if "manifest.webmanifest" not in html_txt:
        extra.append('<link rel="manifest" href="manifest.webmanifest">')
    if "icone.svg" not in html_txt:
        extra.append('<link rel="icon" href="icone.svg">')
    if "livre.js" not in html_txt:
        extra.append('<script src="livre.js" defer></script>')
    if not extra:
        return html_txt
    bloco = "\n" + "\n".join(extra) + "\n"
    if re.search(r"</head>", html_txt, re.I):
        return re.sub(r"</head>", bloco + "</head>", html_txt, count=1, flags=re.I)
    return bloco + html_txt


def _copiar_pagina(origem: Path, destino: Path, nome: str, conf: dict, versao: int):
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("pagina.json", ".*"))
    idx = destino / "index.html"
    idx.write_text(_injetar(idx.read_text(encoding="utf-8")), encoding="utf-8")
    (destino / "manifest.webmanifest").write_text(
        json.dumps(_manifest(nome, conf), ensure_ascii=False, indent=2), encoding="utf-8")
    (destino / "icone.svg").write_text(_icone(conf), encoding="utf-8")
    (destino / "sw.js").write_text(_sw(versao), encoding="utf-8")
    shutil.copy2(RAIZ_KIT / "nucleo" / "livre.js", destino / "livre.js")


def _versoes(area: Area, nome: str) -> list:
    arq = area.site / nome / "versoes.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []


def cmd_publicar(area: Area, nome: str, msg: str) -> int:
    checar_nome(nome)
    conf = area.conf(nome)
    origem = area.paginas / nome
    if not (origem / "index.html").exists():
        raise SystemExit(f"falta {origem / 'index.html'}")
    historico = _versoes(area, nome)
    n = len(historico) + 1
    dest = area.site / nome
    guardadas = dest / "v"
    tmp_v = None
    if guardadas.exists():  # preserva as versões antigas ao recriar a pasta
        tmp_v = area.site / f".v-{nome}-{os.getpid()}"
        shutil.move(str(guardadas), tmp_v)
    _copiar_pagina(origem, dest, nome, conf, n)
    (dest / "v").mkdir(exist_ok=True)
    if tmp_v:
        for item in tmp_v.iterdir():
            shutil.move(str(item), dest / "v" / item.name)
        tmp_v.rmdir()
    _copiar_pagina(origem, dest / "v" / str(n), nome, conf, n)
    soma = hashlib.sha256((origem / "index.html").read_bytes()).hexdigest()[:12]
    historico.append({"n": n, "quando": time.strftime("%Y-%m-%d %H:%M:%S"), "msg": msg or "", "sha": soma})
    (dest / "versoes.json").write_text(json.dumps(historico, ensure_ascii=False, indent=2), encoding="utf-8")
    return n


def cmd_link(area: Area, nome: str, base: str) -> str:
    conf = area.conf(nome)
    url = base.rstrip("/") + f"/{nome}/"
    return url + (f"?k={quote(conf['chave'])}" if conf.get("privada") else "")


# ---------------------------------------------------------------- dados
SQL = """
CREATE TABLE IF NOT EXISTS docs (
  pagina TEXT NOT NULL, colecao TEXT NOT NULL, id TEXT NOT NULL,
  dados TEXT NOT NULL, autor TEXT, criado REAL NOT NULL, atualizado REAL NOT NULL,
  PRIMARY KEY (pagina, colecao, id));
CREATE TABLE IF NOT EXISTS comentarios (
  pagina TEXT NOT NULL, id TEXT NOT NULL, alvo TEXT, autor TEXT, texto TEXT NOT NULL,
  criado REAL NOT NULL, resolvido INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (pagina, id));
"""


class Banco:
    def __init__(self, arq: Path):
        arq.parent.mkdir(parents=True, exist_ok=True)
        self.arq = arq
        self.trava = threading.Lock()
        with self._con() as c:
            c.executescript(SQL)

    def _con(self):
        c = sqlite3.connect(self.arq, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def listar(self, pagina, colecao):
        with self._con() as c:
            rows = c.execute("SELECT * FROM docs WHERE pagina=? AND colecao=? ORDER BY criado",
                             (pagina, colecao)).fetchall()
        return [self._doc(r) for r in rows]

    def pegar(self, pagina, colecao, id_):
        with self._con() as c:
            r = c.execute("SELECT * FROM docs WHERE pagina=? AND colecao=? AND id=?",
                          (pagina, colecao, id_)).fetchone()
        return self._doc(r) if r else None

    def gravar(self, pagina, colecao, id_, dados, autor, juntar=False):
        agora = time.time()
        with self.trava, self._con() as c:
            r = c.execute("SELECT dados, criado, autor FROM docs WHERE pagina=? AND colecao=? AND id=?",
                          (pagina, colecao, id_)).fetchone()
            if r and juntar:
                velho = json.loads(r["dados"])
                velho.update(dados)
                dados = velho
            txt = json.dumps(dados, ensure_ascii=False)
            if len(txt.encode()) > LIMITE_DOC:
                raise ValueError("documento maior que 64 KB")
            c.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?)",
                      (pagina, colecao, id_, txt, r["autor"] if r else autor,  # autor = quem criou
                       r["criado"] if r else agora, agora))
        return self.pegar(pagina, colecao, id_)

    def apagar(self, pagina, colecao, id_):
        with self.trava, self._con() as c:
            return c.execute("DELETE FROM docs WHERE pagina=? AND colecao=? AND id=?",
                             (pagina, colecao, id_)).rowcount

    def comentarios(self, pagina):
        with self._con() as c:
            rows = c.execute("SELECT * FROM comentarios WHERE pagina=? ORDER BY criado", (pagina,)).fetchall()
        return [dict(r) | {"resolvido": bool(r["resolvido"])} for r in rows]

    def comentar(self, pagina, texto, autor, alvo):
        cid = secrets.token_hex(6)
        with self.trava, self._con() as c:
            c.execute("INSERT INTO comentarios VALUES (?,?,?,?,?,?,0)",
                      (pagina, cid, alvo, autor, texto, time.time()))
        return {"id": cid, "alvo": alvo, "autor": autor, "texto": texto, "resolvido": False}

    def resolver(self, pagina, cid):
        with self.trava, self._con() as c:
            return c.execute("UPDATE comentarios SET resolvido=1 WHERE pagina=? AND id=?", (pagina, cid)).rowcount

    def colecoes(self, pagina):
        with self._con() as c:
            return [r[0] for r in c.execute(
                "SELECT DISTINCT colecao FROM docs WHERE pagina=? ORDER BY colecao", (pagina,))]

    @staticmethod
    def _doc(r):
        return {"id": r["id"], "dados": json.loads(r["dados"]), "autor": r["autor"],
                "criado": r["criado"], "atualizado": r["atualizado"]}


def cmd_exportar(area: Area, banco: Banco, nome: str, para: Path) -> Path:
    checar_nome(nome)
    area.conf(nome)
    para = Path(para).resolve() / nome
    para.mkdir(parents=True, exist_ok=True)
    if (area.site / nome).exists():
        shutil.copytree(area.site / nome, para / "site", dirs_exist_ok=True)
    shutil.copytree(area.paginas / nome, para / "fonte", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("pagina.json"))
    dados_dir = para / "dados"
    dados_dir.mkdir(exist_ok=True)
    for col in banco.colecoes(nome):
        docs = banco.listar(nome, col)
        (dados_dir / f"{col}.json").write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
        campos = sorted({k for d in docs for k in d["dados"]})
        with open(dados_dir / f"{col}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "autor", *campos])
            for d in docs:
                w.writerow([d["id"], d["autor"] or "", *[_csv(d["dados"].get(k)) for k in campos]])
    (dados_dir / "comentarios.json").write_text(
        json.dumps(banco.comentarios(nome), ensure_ascii=False, indent=2), encoding="utf-8")
    return para


def _csv(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else ("" if v is None else v)


# ---------------------------------------------------------------- IA opcional
class IA:
    """Qualquer IA, por um comando que lê a pergunta no stdin e responde no stdout.

    Ex.: LIVRE_IA_CMD='ollama run llama3.2'  ·  'claude -p'  ·  'codex exec -'.
    Desligada por padrão. Quem paga é quem roda o servidor (o dono), não quem abre a página.
    """

    def __init__(self, comando: str | None, por_minuto: int = 6, timeout: int = 120):
        self.argv = shlex.split(comando) if comando else None
        self.por_minuto = por_minuto
        self.timeout = timeout
        self.uso: dict[str, list[float]] = {}
        self.trava = threading.Lock()

    def perguntar(self, quem: str, pergunta: str) -> str:
        if not self.argv:
            raise PermissionError("IA desligada neste servidor (defina LIVRE_IA_CMD)")
        agora = time.time()
        with self.trava:
            janela = [t for t in self.uso.get(quem, []) if agora - t < 60]
            if len(janela) >= self.por_minuto:
                raise OverflowError("limite de perguntas por minuto")
            janela.append(agora)
            self.uso[quem] = janela
        r = subprocess.run(self.argv, input=pergunta, capture_output=True, text=True,
                           timeout=self.timeout, shell=False)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or "falhou").strip()[-300:])
        return r.stdout.strip()


# ---------------------------------------------------------------- servidor
class App:
    def __init__(self, area: Area, banco: Banco, ia: IA):
        self.area, self.banco, self.ia = area, banco, ia


def fazer_handler(app: App):
    class H(BaseHTTPRequestHandler):
        server_version = f"artefatos-livres/{VERSAO}"

        def log_message(self, fmt, *args):  # silencioso; LIVRE_LOG=1 liga
            if os.environ.get("LIVRE_LOG"):
                sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

        # ---------- utilidades
        def _json(self, codigo, obj, cookies=()):
            corpo = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            for c in cookies:
                self.send_header("Set-Cookie", c)
            self.end_headers()
            self.wfile.write(corpo)

        def _erro(self, codigo, msg):
            self._json(codigo, {"erro": msg})

        def _corpo(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > LIMITE_CORPO:
                raise ValueError("corpo grande demais")
            bruto = self.rfile.read(n) if n else b"{}"
            obj = json.loads(bruto or b"{}")
            if not isinstance(obj, dict):
                raise ValueError("envie um objeto JSON")
            return obj

        def _cookies(self):
            c = SimpleCookie()
            try:
                c.load(self.headers.get("Cookie") or "")
            except Exception:
                pass
            return {k: v.value for k, v in c.items()}

        def _quem(self):
            nome = unquote(self.headers.get("X-Livre-Nome") or self._cookies().get("livre_nome") or "").strip()
            return nome[:60] or "anônimo"

        def _autorizado(self, nome, qs):
            """Página privada: precisa da chave (?k= ou cookie). Devolve (ok, cookie_a_gravar)."""
            try:
                conf = app.area.conf(nome)
            except SystemExit:
                return None, None
            if not conf.get("privada"):
                return True, None
            chave = conf["chave"]
            dada = (qs.get("k") or [None])[0]
            if dada and secrets.compare_digest(dada, chave):
                return True, f"k_{nome}={chave}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000"
            if secrets.compare_digest(self._cookies().get(f"k_{nome}", ""), chave):
                return True, None
            api_chave = self.headers.get("X-Livre-Chave") or ""
            if api_chave and secrets.compare_digest(api_chave, chave):
                return True, None
            return False, None

        # ---------- rotas
        def do_GET(self):
            self._rota("GET")

        def do_POST(self):
            self._rota("POST")

        def do_PUT(self):
            self._rota("PUT")

        def do_PATCH(self):
            self._rota("PATCH")

        def do_DELETE(self):
            self._rota("DELETE")

        def _rota(self, metodo):
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            partes = [p for p in u.path.split("/") if p]
            try:
                if not partes:
                    return self._indice() if metodo == "GET" else self._erro(405, "método")
                if partes[0] == "api":
                    return self._api(metodo, partes[1:], qs)
                if metodo != "GET":
                    return self._erro(405, "método")
                return self._arquivo(partes, qs, u.path.endswith("/"))
            except (ValueError, json.JSONDecodeError) as e:
                return self._erro(400, str(e))

        def _indice(self):
            itens = []
            for p in sorted(app.area.paginas.glob("*/pagina.json")):
                conf = json.loads(p.read_text(encoding="utf-8"))
                if not conf.get("privada") and (app.area.site / p.parent.name / "index.html").exists():
                    itens.append(f'<li><a href="/{p.parent.name}/">{html.escape(conf["titulo"])}</a></li>')
            corpo = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                     "<title>Páginas</title><body style='font:16px system-ui;background:#0c0c10;color:#eee;"
                     "padding:24px'><h1 style='color:#FACC15'>Páginas públicas</h1><ul>"
                     + ("".join(itens) or "<li>nenhuma página pública (as privadas só abrem pelo link com chave)</li>")
                     + "</ul></body>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _arquivo(self, partes, qs, barra):
            nome = partes[0]
            if not NOME_OK.match(nome):
                return self._erro(404, "não encontrado")
            ok, cookie = self._autorizado(nome, qs)
            if ok is None or not (app.area.site / nome).exists():
                return self._erro(404, "não encontrado")
            if not ok:
                return self._erro(403, "página privada: abra pelo link com a chave")
            if len(partes) == 1 and not barra:
                self.send_response(301)
                self.send_header("Location", f"/{nome}/" + (f"?{urlparse(self.path).query}" if qs else ""))
                self.end_headers()
                return
            base = (app.area.site / nome).resolve()
            alvo = (base / "/".join(partes[1:])).resolve()
            if base not in alvo.parents and alvo != base:
                return self._erro(404, "não encontrado")
            if alvo.is_dir():
                alvo = alvo / "index.html"
            if not alvo.is_file():
                return self._erro(404, "não encontrado")
            dados = alvo.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TIPOS.get(alvo.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(dados)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(dados)

        def _api(self, metodo, p, qs):
            if not p or not NOME_OK.match(p[0]):
                return self._erro(404, "rota")
            nome = p[0]
            ok, _ = self._autorizado(nome, qs)
            if ok is None:
                return self._erro(404, "página não existe")
            if not ok:
                return self._erro(403, "sem chave")
            quem = self._quem()
            resto = p[1:]
            b = app.banco
            if resto == ["eu"] and metodo == "GET":
                return self._json(200, {"nome": quem, "ia": bool(app.ia.argv), "versao": VERSAO})
            if resto == ["versoes"] and metodo == "GET":
                return self._json(200, _versoes(app.area, nome))
            if resto[:1] == ["db"] and len(resto) >= 2:
                col = resto[1]
                if not COLECAO_OK.match(col):
                    return self._erro(400, "coleção inválida")
                if len(resto) == 2:
                    if metodo == "GET":
                        return self._json(200, b.listar(nome, col))
                    if metodo == "POST":
                        corpo = self._corpo()
                        did = str(corpo.get("id") or secrets.token_hex(6))[:64]
                        dados = corpo.get("dados", {})
                        if not isinstance(dados, dict):
                            raise ValueError("'dados' precisa ser objeto")
                        return self._json(201, b.gravar(nome, col, did, dados, quem))
                    return self._erro(405, "método")
                did = resto[2][:64]
                if metodo == "GET":
                    d = b.pegar(nome, col, did)
                    return self._json(200, d) if d else self._erro(404, "doc não existe")
                if metodo in ("PUT", "PATCH"):
                    dados = self._corpo().get("dados", {})
                    if not isinstance(dados, dict):
                        raise ValueError("'dados' precisa ser objeto")
                    return self._json(200, b.gravar(nome, col, did, dados, quem, juntar=metodo == "PATCH"))
                if metodo == "DELETE":
                    return self._json(200, {"apagados": b.apagar(nome, col, did)})
                return self._erro(405, "método")
            if resto[:1] == ["comentarios"]:
                if len(resto) == 1 and metodo == "GET":
                    return self._json(200, b.comentarios(nome))
                if len(resto) == 1 and metodo == "POST":
                    c = self._corpo()
                    texto = str(c.get("texto") or "").strip()[:2000]
                    if not texto:
                        raise ValueError("comentário vazio")
                    return self._json(201, b.comentar(nome, texto, quem, str(c.get("alvo") or "")[:120]))
                if len(resto) == 3 and resto[2] == "resolver" and metodo == "POST":
                    return self._json(200, {"resolvidos": b.resolver(nome, resto[1])})
                return self._erro(405, "método")
            if resto == ["ia"] and metodo == "POST":
                pergunta = str(self._corpo().get("pergunta") or "").strip()[:8000]
                if not pergunta:
                    raise ValueError("pergunta vazia")
                try:
                    return self._json(200, {"resposta": app.ia.perguntar(f"{nome}:{quem}", pergunta)})
                except PermissionError as e:
                    return self._erro(501, str(e))
                except OverflowError as e:
                    return self._erro(429, str(e))
                except (RuntimeError, subprocess.TimeoutExpired) as e:
                    return self._erro(502, f"IA falhou: {e}")
            return self._erro(404, "rota")

    return H


def criar_servidor(area: Area, host: str, porta: int, ia_cmd: str | None) -> ThreadingHTTPServer:
    area.preparar()
    app = App(area, Banco(area.dados / "livre.db"), IA(ia_cmd))
    return ThreadingHTTPServer((host, porta), fazer_handler(app))


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="artefatos.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", default=os.environ.get("LIVRE_AREA", "."),
                    help="pasta com paginas/ site/ dados/ (padrão: a atual)")
    ap.add_argument("--versao", action="version", version=VERSAO)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("novo"); s.add_argument("nome"); s.add_argument("--titulo", required=True)
    s.add_argument("--publica", action="store_true", help="sem chave (aparece na lista da raiz)")
    s.add_argument("--modelo", default="tarefas", help="pasta em modelos/ (tarefas, inscricoes, em-branco)")
    s = sub.add_parser("publicar"); s.add_argument("nome"); s.add_argument("-m", "--msg", default="")
    s = sub.add_parser("versoes"); s.add_argument("nome")
    s = sub.add_parser("link"); s.add_argument("nome")
    s.add_argument("--base", default=os.environ.get("LIVRE_BASE", "http://127.0.0.1:8787"))
    s = sub.add_parser("servir"); s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--porta", type=int, default=8787)
    s = sub.add_parser("exportar"); s.add_argument("nome"); s.add_argument("--para", required=True)
    a = ap.parse_args(argv)
    area = Area(Path(a.area))

    if a.cmd == "novo":
        pasta = cmd_novo(area, a.nome, a.titulo, a.publica, a.modelo)
        print(f"criada: {pasta}/index.html  (edite à mão ou peça a qualquer IA; contrato em CONTRATO.md)")
        print(f"depois: python3 artefatos.py publicar {a.nome}")
    elif a.cmd == "publicar":
        n = cmd_publicar(area, a.nome, a.msg)
        print(f"publicada versão {n}: o link fixo /{a.nome}/ mostra esta; a anterior fica em /{a.nome}/v/{n - 1}/" if n > 1
              else f"publicada versão 1 em /{a.nome}/")
    elif a.cmd == "versoes":
        for v in _versoes(area, checar_nome(a.nome)):
            print(f"v{v['n']}  {v['quando']}  {v['sha']}  {v['msg']}")
    elif a.cmd == "link":
        print(cmd_link(area, checar_nome(a.nome), a.base))
    elif a.cmd == "servir":
        ia_cmd = os.environ.get("LIVRE_IA_CMD")
        srv = criar_servidor(area, a.host, a.porta, ia_cmd)
        print(f"servindo {area.base} em http://{a.host}:{a.porta}/  (IA: {'ligada' if ia_cmd else 'desligada'})")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
    elif a.cmd == "exportar":
        destino = cmd_exportar(area, Banco(area.dados / "livre.db"), a.nome, Path(a.para))
        print(f"exportado para {destino} (site/, fonte/, dados/*.json e *.csv)")


if __name__ == "__main__":
    main()
