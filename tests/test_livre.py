"""Testes do artefatos-livres: tudo roda sem nenhuma IA e sem internet.

python3 -m unittest discover -s tests -v
"""
import csv
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import artefatos as A  # noqa: E402


def pedir(url, metodo="GET", corpo=None, cab=None):
    dados = None if corpo is None else json.dumps(corpo).encode()
    h = {"Content-Type": "application/json"}
    h.update(cab or {})
    req = urllib.request.Request(url, data=dados, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


class Servidor:
    def __init__(self, area, ia_cmd=None):
        self.srv = A.criar_servidor(area, "127.0.0.1", 0, ia_cmd)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    def parar(self):
        self.srv.shutdown()
        self.srv.server_close()


class TestKit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.area = A.Area(Path(self.tmp.name))
        self.area.preparar()
        A.cmd_novo(self.area, "tarefas", "Tarefas da semana", publica=False, modelo="tarefas")
        A.cmd_novo(self.area, "mural", "Mural aberto", publica=True, modelo="em-branco")
        A.cmd_publicar(self.area, "tarefas", "primeira")
        A.cmd_publicar(self.area, "mural", "")
        self.chave = self.area.conf("tarefas")["chave"]
        self.s = Servidor(self.area)

    def tearDown(self):
        self.s.parar()
        self.tmp.cleanup()

    # --- link e privacidade
    def test_privada_sem_chave_403_e_com_chave_200(self):
        st, _, _ = pedir(self.s.base + "/tarefas/")
        self.assertEqual(st, 403)
        st, corpo, cab = pedir(self.s.base + f"/tarefas/?k={self.chave}")
        self.assertEqual(st, 200)
        self.assertIn(b"Tarefas da semana", corpo)
        self.assertIn("k_tarefas=", cab.get("Set-Cookie", ""))

    def test_chave_errada_403(self):
        st, _, _ = pedir(self.s.base + "/tarefas/?k=errada")
        self.assertEqual(st, 403)

    def test_cookie_da_chave_abre_sem_query(self):
        st, _, _ = pedir(self.s.base + "/tarefas/", cab={"Cookie": f"k_tarefas={self.chave}"})
        self.assertEqual(st, 200)

    def test_cookie_da_pagina_vale_na_api(self):
        _, _, cab = pedir(self.s.base + f"/tarefas/?k={self.chave}")
        cookie = cab["Set-Cookie"]
        self.assertIn("Path=/;", cookie)  # com Path=/tarefas/ a API (/api/tarefas/) não receberia a chave
        par = cookie.split(";")[0]
        st, _, _ = pedir(self.s.base + "/api/tarefas/eu", cab={"Cookie": par})
        self.assertEqual(st, 200)

    def test_chave_com_acento_nao_derruba(self):
        st, _, _ = pedir(self.s.base + "/tarefas/?k=%C3%A7%C3%A3o")
        self.assertEqual(st, 403)

    def test_manifest_com_credenciais_e_icone_publico(self):
        _, corpo, _ = pedir(self.s.base + f"/tarefas/?k={self.chave}")
        self.assertIn(b'crossorigin="use-credentials"', corpo)  # o navegador manda o cookie ao buscar o manifest
        st, _, _ = pedir(self.s.base + "/tarefas/icone.svg")
        self.assertEqual(st, 200)
        st, _, _ = pedir(self.s.base + "/tarefas/manifest.webmanifest")
        self.assertEqual(st, 403)

    def test_indice_lista_so_publicas(self):
        st, corpo, _ = pedir(self.s.base + "/")
        self.assertEqual(st, 200)
        self.assertIn(b"Mural aberto", corpo)
        self.assertNotIn(b"Tarefas da semana", corpo)

    def test_link_impresso_tem_chave_so_na_privada(self):
        self.assertIn("?k=", A.cmd_link(self.area, "tarefas", "https://x.dev"))
        self.assertEqual(A.cmd_link(self.area, "mural", "https://x.dev/"), "https://x.dev/mural/")

    def test_nao_escapa_da_pasta(self):
        st, _, _ = pedir(self.s.base + "/mural/../dados/livre.db")
        self.assertIn(st, (403, 404))
        st, _, _ = pedir(self.s.base + "/mural/%2e%2e/%2e%2e/artefatos.py")
        self.assertEqual(st, 404)

    # --- versões no mesmo link
    def test_versoes_mesmo_link(self):
        idx = self.area.paginas / "mural" / "index.html"
        idx.write_text(idx.read_text(encoding="utf-8").replace("Mural aberto</h1>", "Mural aberto v2</h1>"),
                       encoding="utf-8")
        n = A.cmd_publicar(self.area, "mural", "segunda")
        self.assertEqual(n, 2)
        _, atual, _ = pedir(self.s.base + "/mural/")
        _, v1, _ = pedir(self.s.base + "/mural/v/1/")
        self.assertIn(b"Mural aberto v2", atual)
        self.assertNotIn(b"Mural aberto v2", v1)
        st, corpo, _ = pedir(self.s.base + "/api/mural/versoes")
        self.assertEqual([v["n"] for v in json.loads(corpo)], [1, 2])
        A.cmd_publicar(self.area, "mural", "terceira")  # versões antigas continuam lá
        self.assertTrue((self.area.site / "mural" / "v" / "1" / "index.html").exists())
        self.assertTrue((self.area.site / "mural" / "v" / "3" / "index.html").exists())

    # --- instalar como app
    def test_app_instalavel(self):
        _, corpo, _ = pedir(self.s.base + "/mural/")
        self.assertIn(b'rel="manifest"', corpo)
        self.assertIn(b"livre.js", corpo)
        st, man, cab = pedir(self.s.base + "/mural/manifest.webmanifest")
        self.assertEqual(st, 200)
        m = json.loads(man)
        self.assertEqual(m["display"], "standalone")
        self.assertTrue(m["icons"])
        self.assertIn("manifest", cab["Content-Type"])
        st, sw, _ = pedir(self.s.base + "/mural/sw.js")
        self.assertEqual(st, 200)
        self.assertIn(b"livre-v1", sw)

    # --- dados compartilhados
    def test_dados_compartilhados_entre_pessoas(self):
        ana = {"X-Livre-Chave": self.chave, "X-Livre-Nome": "Ana"}
        bia = {"X-Livre-Chave": self.chave, "X-Livre-Nome": "Bia"}
        st, d, _ = pedir(self.s.base + "/api/tarefas/db/tarefas", "POST", {"dados": {"texto": "Fechar caixa", "feita": False}}, ana)
        self.assertEqual(st, 201)
        doc = json.loads(d)
        st, lista, _ = pedir(self.s.base + "/api/tarefas/db/tarefas", cab=bia)
        lista = json.loads(lista)
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["autor"], "Ana")
        st, d, _ = pedir(self.s.base + f"/api/tarefas/db/tarefas/{doc['id']}", "PATCH", {"dados": {"feita": True}}, bia)
        d = json.loads(d)
        self.assertEqual(d["dados"], {"texto": "Fechar caixa", "feita": True})
        self.assertEqual(d["autor"], "Ana")  # quem edita não vira autor
        st, _, _ = pedir(self.s.base + f"/api/tarefas/db/tarefas/{doc['id']}", "DELETE", cab=ana)
        self.assertEqual(st, 200)
        _, lista, _ = pedir(self.s.base + "/api/tarefas/db/tarefas", cab=ana)
        self.assertEqual(json.loads(lista), [])

    def test_nome_com_acento(self):
        cab = {"X-Livre-Chave": self.chave, "X-Livre-Nome": "Jos%C3%A9"}
        _, d, _ = pedir(self.s.base + "/api/tarefas/eu", cab=cab)
        self.assertEqual(json.loads(d)["nome"], "José")

    def test_api_privada_sem_chave_403(self):
        st, _, _ = pedir(self.s.base + "/api/tarefas/db/tarefas")
        self.assertEqual(st, 403)

    def test_entrada_ruim_400(self):
        cab = {"X-Livre-Chave": self.chave}
        st, _, _ = pedir(self.s.base + "/api/tarefas/db/tar..fas", cab=cab)
        self.assertEqual(st, 400)
        st, _, _ = pedir(self.s.base + "/api/tarefas/db/tarefas", "POST", {"dados": [1, 2]}, cab)
        self.assertEqual(st, 400)
        grande = {"dados": {"x": "a" * (70 * 1024)}}
        st, _, _ = pedir(self.s.base + "/api/tarefas/db/tarefas", "POST", grande, cab)
        self.assertEqual(st, 400)

    # --- comentários
    def test_comentarios(self):
        cab = {"X-Livre-Nome": "Caio"}
        st, c, _ = pedir(self.s.base + "/api/mural/comentarios", "POST", {"texto": "Troca 'atrasada' por dias", "alvo": "#lista"}, cab)
        self.assertEqual(st, 201)
        cid = json.loads(c)["id"]
        pedir(self.s.base + f"/api/mural/comentarios/{cid}/resolver", "POST", {})
        _, l, _ = pedir(self.s.base + "/api/mural/comentarios")
        l = json.loads(l)
        self.assertEqual(l[0]["autor"], "Caio")
        self.assertTrue(l[0]["resolvido"])

    # --- IA opcional
    def test_ia_desligada_501(self):
        st, _, _ = pedir(self.s.base + "/api/mural/ia", "POST", {"pergunta": "oi"})
        self.assertEqual(st, 501)

    def test_ia_por_comando_qualquer(self):
        self.s.parar()
        # um "modelo" de mentira: o comando só devolve a pergunta em maiúsculas
        self.s = Servidor(self.area, ia_cmd=f"{sys.executable} -c \"import sys;print(sys.stdin.read().upper())\"")
        st, r, _ = pedir(self.s.base + "/api/mural/ia", "POST", {"pergunta": "resuma a semana"})
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(r)["resposta"], "RESUMA A SEMANA")
        for _ in range(6):
            st, _, _ = pedir(self.s.base + "/api/mural/ia", "POST", {"pergunta": "x"})
        self.assertEqual(st, 429)  # limite por minuto

    # --- porta de saída
    def test_exportar_json_csv(self):
        cab = {"X-Livre-Chave": self.chave, "X-Livre-Nome": "Ana"}
        pedir(self.s.base + "/api/tarefas/db/tarefas", "POST", {"id": "t1", "dados": {"texto": "A", "feita": True}}, cab)
        destino = A.cmd_exportar(self.area, A.Banco(self.area.dados / "livre.db"), "tarefas",
                                 Path(self.tmp.name) / "saida")
        self.assertTrue((destino / "site" / "index.html").exists())
        self.assertTrue((destino / "fonte" / "index.html").exists())
        self.assertFalse((destino / "fonte" / "pagina.json").exists())  # a chave não sai
        docs = json.loads((destino / "dados" / "tarefas.json").read_text(encoding="utf-8"))
        self.assertEqual(docs[0]["id"], "t1")
        with open(destino / "dados" / "tarefas.csv", encoding="utf-8") as f:
            linhas = list(csv.reader(f))
        self.assertEqual(linhas[0], ["id", "autor", "feita", "texto"])
        self.assertEqual(linhas[1], ["t1", "Ana", "True", "A"])

    def test_nome_invalido(self):
        with self.assertRaises(SystemExit):
            A.cmd_novo(self.area, "../x", "X", True, "em-branco")


if __name__ == "__main__":
    unittest.main()
