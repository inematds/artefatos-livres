// artefatos-livres — livre.js
// Dá à página: dados compartilhados (livre.db), comentários (livre.comentarios), IA opcional (livre.perguntar),
// quem está vendo (livre.nome) e "instalar como app" (service worker + manifest).
// Sem servidor (aberta do disco ou num host estático como o GitHub Pages), cai no modo local:
// os dados ficam só neste navegador e a página avisa.
(function () {
  "use strict";
  const segs = location.pathname.split("/").filter(Boolean);
  const pagina = segs[0] || "";
  const api = "/api/" + pagina;
  const chaveNome = "livre_nome";
  let modo = "carregando";
  const ouvintes = [];

  function lerLocal(k, padrao) {
    try { const v = localStorage.getItem(k); return v === null ? padrao : JSON.parse(v); } catch (e) { return padrao; }
  }
  function gravarLocal(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* sem storage */ } }

  let nome = lerLocal(chaveNome, "");
  function cabecalhos() {
    const h = { "Content-Type": "application/json" };
    if (nome) h["X-Livre-Nome"] = encodeURIComponent(nome).slice(0, 180);
    return h;
  }
  async function pedir(metodo, caminho, corpo) {
    const r = await fetch(api + caminho, {
      method: metodo, headers: cabecalhos(), credentials: "same-origin",
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.erro || ("HTTP " + r.status));
    return j;
  }

  // ---------- modo local (sem servidor)
  const chaveCol = (c) => "livre_db_" + pagina + "_" + c;
  const local = {
    listar: (c) => lerLocal(chaveCol(c), []),
    gravar(c, id, dados, juntar) {
      const docs = local.listar(c); const agora = Date.now() / 1000;
      const i = docs.findIndex((d) => d.id === id);
      if (i >= 0) { docs[i].dados = juntar ? Object.assign({}, docs[i].dados, dados) : dados; docs[i].atualizado = agora; }
      else docs.push({ id, dados, autor: nome || "você", criado: agora, atualizado: agora });
      gravarLocal(chaveCol(c), docs); return docs.find((d) => d.id === id);
    },
    apagar(c, id) { gravarLocal(chaveCol(c), local.listar(c).filter((d) => d.id !== id)); return { apagados: 1 }; },
  };
  const novoId = () => Math.random().toString(16).slice(2, 14);

  function db(colecao) {
    return {
      async listar() { return modo === "servidor" ? pedir("GET", "/db/" + colecao) : local.listar(colecao); },
      async criar(dados, id) {
        const r = modo === "servidor" ? await pedir("POST", "/db/" + colecao, { id, dados })
          : local.gravar(colecao, id || novoId(), dados, false);
        avisar(); return r;
      },
      async trocar(id, dados) {
        const r = modo === "servidor" ? await pedir("PUT", "/db/" + colecao + "/" + encodeURIComponent(id), { dados })
          : local.gravar(colecao, id, dados, false);
        avisar(); return r;
      },
      async juntar(id, dados) {
        const r = modo === "servidor" ? await pedir("PATCH", "/db/" + colecao + "/" + encodeURIComponent(id), { dados })
          : local.gravar(colecao, id, dados, true);
        avisar(); return r;
      },
      async apagar(id) {
        const r = modo === "servidor" ? await pedir("DELETE", "/db/" + colecao + "/" + encodeURIComponent(id))
          : local.apagar(colecao, id);
        avisar(); return r;
      },
    };
  }

  const comentarios = {
    async listar() { return modo === "servidor" ? pedir("GET", "/comentarios") : lerLocal("livre_com_" + pagina, []); },
    async criar(texto, alvo) {
      if (modo === "servidor") return pedir("POST", "/comentarios", { texto, alvo: alvo || "" });
      const l = lerLocal("livre_com_" + pagina, []);
      const c = { id: novoId(), texto, alvo: alvo || "", autor: nome || "você", criado: Date.now() / 1000, resolvido: false };
      l.push(c); gravarLocal("livre_com_" + pagina, l); return c;
    },
    async resolver(id) { if (modo === "servidor") return pedir("POST", "/comentarios/" + id + "/resolver"); },
  };

  async function perguntar(pergunta) {
    if (modo !== "servidor") throw new Error("IA só funciona com o servidor ligado");
    return (await pedir("POST", "/ia", { pergunta })).resposta;
  }

  // atualização simples para quem está com a página aberta: relê a cada 5 s quando visível
  function avisar() { ouvintes.forEach((f) => { try { f(); } catch (e) { console.error(e); } }); }
  function aoMudar(f) { ouvintes.push(f); return f; }
  setInterval(() => { if (modo === "servidor" && document.visibilityState === "visible") avisar(); }, 5000);

  function definirNome(n) { nome = String(n || "").trim().slice(0, 60); gravarLocal(chaveNome, nome); avisar(); }

  // ---------- painel de comentários (some com <body data-sem-comentarios>)
  function painel() {
    if (document.body.hasAttribute("data-sem-comentarios")) return;
    const css = document.createElement("style");
    css.textContent = `.livre-bt{position:fixed;right:16px;bottom:16px;z-index:9999;background:#FACC15;color:#0c0c10;border:0;
      border-radius:999px;padding:10px 16px;font:600 14px system-ui;cursor:pointer;box-shadow:0 4px 16px #0006}
      .livre-pn{position:fixed;right:16px;bottom:64px;z-index:9999;width:min(360px,calc(100vw - 32px));max-height:60vh;
      overflow:auto;background:#16161c;color:#eee;border:1px solid #333;border-radius:12px;padding:12px;font:14px system-ui;display:none}
      .livre-pn textarea,.livre-pn input{width:100%;box-sizing:border-box;background:#0c0c10;color:#eee;border:1px solid #444;
      border-radius:8px;padding:8px;margin:4px 0;font:14px system-ui}.livre-pn .c{border-top:1px solid #2a2a30;padding:6px 0}
      .livre-pn .c.ok{opacity:.5}.livre-pn small{color:#aaa}.livre-pn button{background:#FACC15;border:0;border-radius:8px;padding:6px 10px;cursor:pointer}
      .livre-aviso{position:fixed;left:16px;bottom:16px;z-index:9999;background:#3b2f05;color:#FACC15;padding:6px 10px;border-radius:8px;font:12px system-ui}`;
    document.head.appendChild(css);
    const bt = document.createElement("button"); bt.className = "livre-bt"; bt.textContent = "💬 Comentários";
    const pn = document.createElement("div"); pn.className = "livre-pn";
    pn.innerHTML = `<b>Comentários</b><input class="livre-nome" placeholder="Seu nome"><textarea rows="3" placeholder="Escreva aqui"></textarea>
      <button class="livre-enviar">Enviar</button><div class="livre-lista"></div>`;
    document.body.append(bt, pn);
    const inNome = pn.querySelector(".livre-nome"); inNome.value = nome;
    inNome.addEventListener("change", () => definirNome(inNome.value));
    bt.onclick = () => { pn.style.display = pn.style.display === "block" ? "none" : "block"; desenhar(); };
    pn.querySelector(".livre-enviar").onclick = async () => {
      const ta = pn.querySelector("textarea"); if (!ta.value.trim()) return;
      if (inNome.value) definirNome(inNome.value);
      await comentarios.criar(ta.value.trim()); ta.value = ""; desenhar();
    };
    async function desenhar() {
      if (pn.style.display !== "block") return;
      const l = await comentarios.listar().catch(() => []);
      const lista = pn.querySelector(".livre-lista"); lista.textContent = "";
      l.slice().reverse().forEach((c) => {
        const d = document.createElement("div"); d.className = "c" + (c.resolvido ? " ok" : "");
        const s = document.createElement("small"); s.textContent = (c.autor || "") + " · " + new Date(c.criado * 1000).toLocaleString();
        const p = document.createElement("div"); p.textContent = c.texto;
        d.append(s, p); lista.appendChild(d);
      });
    }
    aoMudar(desenhar);
  }

  async function iniciar() {
    try { await pedir("GET", "/eu"); modo = "servidor"; } catch (e) { modo = "local"; }
    if ("serviceWorker" in navigator && location.protocol !== "file:") {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    }
    if (document.body) painel();
    if (modo === "local" && document.body && !document.body.hasAttribute("data-sem-aviso")) {
      const a = document.createElement("div"); a.className = "livre-aviso";
      a.textContent = "Modo local: os dados ficam só neste navegador"; document.body.appendChild(a);
    }
    window.dispatchEvent(new CustomEvent("livre:pronto", { detail: { modo } }));
    avisar();
  }

  window.livre = {
    db, comentarios, perguntar, aoMudar, definirNome,
    get nome() { return nome; }, get modo() { return modo; }, pagina,
    pronto: new Promise((ok) => window.addEventListener("livre:pronto", () => ok(modo), { once: true })),
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
