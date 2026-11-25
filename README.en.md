# Artefatos Livres

[![Artefatos Livres: your pages by link, without depending on Claude](guia/assets/banner-en.jpg)](https://inematds.github.io/artefatos-livres/guia/en/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## What it is

You want the convenience of sending a link and having everyone use the same page, without handing your team and your data over to a single company. Artefatos Livres is a free kit that does, on a computer or server of your own, what Claude Artifacts do: a page opened by link (private by default), a new version at the same address, install as an app, shared lists and sign-ups, and comments. Any AI writes the page (Claude, Codex, Gemini, or a model on your PC), or you can write it yourself. To use it, all you need is a computer with Python and to ask your AI to install it.

## 📖 User guide

Full guide (landing + step by step): **https://inematds.github.io/artefatos-livres/guia/en/**

## How to start: paste this into your AI (Claude Code, Codex, Gemini CLI…)

> Read the repository https://github.com/inematds/artefatos-livres (the README and CONTRATO.md). Then ask me which pages, lists, or spreadsheets my team uses today by link (including Claude artifacts) and tell me, in plain language: which ones could become an Artefatos Livres page, where to run it (on my computer, on a VPS, or just as a static page), and what I would lose compared to Claude. Don't install or change anything before my yes. With my yes: download the kit, run the tests, create the first page from the template that makes the most sense, publish it, start the server, and send me the link so I can open it.

**Use without installing?** There is no online version: the idea is for the page to stay with you. The closest option is publishing just the page (without shared data) on free static hosting.
**Where to download?** There is no installer: [kit ZIP](https://github.com/inematds/artefatos-livres/archive/refs/heads/main.zip) or `git clone`.

---

# Technical installation

## Why it exists

Claude Artifacts have become a place to work: page by link, versions, data, comments, and now
"install as an app". It works well, but the page, the data, and who can open it stay in Anthropic's account: without an account, the AI part of the page doesn't work,
and docs and sheets only open after signing in. Anthropic's own help center says: for an internal tool with a backend,
publish it on your own infrastructure. That is what this kit does, in the same format, with the source of truth in files of your own.

## What the kit does × Claude Artifacts

| Feature | Claude Artifacts | artefatos-livres |
|---|---|---|
| Page by link, private by default | yes | yes (link with key; no key = 403) |
| New version at the same link | yes | yes (`/nome/` = latest, `/nome/v/N/` = each version) |
| Install as an app | beta; Mac and Windows; no Linux, web, or phone | PWA: Chrome/Edge on Windows, Mac, Linux, Android (needs HTTPS or localhost) |
| Shared data (list, sign-up) | yes | yes (SQLite on your server) |
| Comments on the page | yes, and tag Claude to fix | yes (💬 panel); you ask whichever AI you want to make the fix |
| The page calls AI | yes, on the quota of whoever opens it | optional: any command (`claude -p`, `codex exec -`, `ollama run …`) on the owner's account |
| Connectors (Gmail, Slack, BigQuery…) | yes | **no**: the page only sees its own server |
| Ready-made Docs/Slides/Sheets templates | yes | no; there are 3 simple templates (tasks, sign-ups, blank) |
| Whoever opens it needs an account | most open without signing in; docs/sheets and the AI or connector parts require an account | no; just the link (the AI, if enabled, runs on the owner's account) |
| Leave taking everything | exports the content | `exportar`: HTML + data in JSON and CSV, without the key |

## The process, from start to finish

| # | Step | Command | Who |
|---|---|---|---|
| 1 | Create the page from a template | `python3 artefatos.py novo tarefas --titulo "Tarefas da equipe"` | 🧠 you |
| 2 | Write/adjust the HTML (by hand or by asking any AI with `CONTRATO.md`) | edit `paginas/tarefas/index.html` | 🧠 you / 🤖 AI |
| 3 | Publish the version | `python3 artefatos.py publicar tarefas -m "primeira"` | ⚙️ script |
| 4 | Start the server | `python3 artefatos.py servir --porta 8787` | ⚙️ script |
| 5 | Get the link to send | `python3 artefatos.py link tarefas --base https://seu.dominio` | ⚙️ script |
| 6 | Changed something? Edit and publish again: the link doesn't change | `python3 artefatos.py publicar tarefas -m "prazo"` | 🧠 / ⚙️ |
| 7 | See the versions | `python3 artefatos.py versoes tarefas` | ⚙️ |
| 8 | (optional) Turn on the page's AI | `LIVRE_IA_CMD='ollama run llama3.2' python3 artefatos.py servir` | 🧠 |
| 9 | Take everything away | `python3 artefatos.py exportar tarefas --para ~/backup` | ⚙️ |

Requirement: Python 3.9+. Nothing to install.

## Where to run

- **On your PC, on the company network**: `servir --host 0.0.0.0` and the link with the machine's IP. Installing as an app requires HTTPS
  (or `localhost`), so on the local network the page opens, but the install button may not appear.
- **On your own VPS with HTTPS**: Caddy in front (`seu.dominio { reverse_proxy 127.0.0.1:8787 }`) and the server as a
  systemd service. Then the link works for anyone and "install app" shows up in Chrome/Edge.
- **Static only (GitHub Pages, any hosting)**: upload the `site/<nome>/` folder. The page opens and installs, but
  the data stays in each person's browser (local mode) — good for a report, a presentation, a read-only dashboard.

## Security

- The link key is the access: whoever has the link can open and edit. To remove someone's access, change the `chave` in
  `paginas/<nome>/pagina.json` and send the new link.
- The server only serves what is in `site/`, limits the size of the data (256 KB per request, 64 KB per document) and the
  AI (6 questions per minute per person). The page calls the AI through the command that **you** configured; the text goes through
  stdin, without a shell.
- It is not a system with per-person login or roles (admin/reader). Need that? Use a tool built for it.

## Tests

```bash
python3 -m unittest discover -s tests -v       # 18 testes: link, chave, versões, app, dados, comentários, IA, exportar
node tests/navegador.mjs "<link com chave>" .   # Chromium real: duas pessoas na mesma lista
```

## Files

`artefatos.py` (CLI + server) · `nucleo/livre.js` (data, comments, AI, app) · `nucleo/sw.js` (offline) ·
`modelos/` (tasks, sign-ups, blank) · `CONTRATO.md` (for any AI) · `guia/` (project page).

MIT License. Made by the [INEMA.CLUB](https://inema.club) community.
