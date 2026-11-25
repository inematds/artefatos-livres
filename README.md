# Artefatos Livres

[![Artefatos Livres: suas páginas por link, sem depender do Claude](guia/assets/banner.jpg)](https://inematds.github.io/artefatos-livres/guia/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## O que é

Você quer a praticidade de mandar um link e todo mundo usar a mesma página, sem entregar a sua equipe e os seus dados a uma única empresa. O Artefatos Livres é um kit gratuito que faz, num computador ou servidor seu, o que os Artifacts do Claude fazem: página aberta por link (privada por padrão), versão nova no mesmo endereço, instalar como aplicativo, lista e cadastro compartilhados e comentários. Qualquer IA escreve a página (Claude, Codex, Gemini ou um modelo no seu PC), ou você mesmo. Para usar, basta um computador com Python e pedir à sua IA que instale.

## 📖 Guia de uso

Guia completo (landing + passo a passo): **https://inematds.github.io/artefatos-livres/guia/**

## Como começar: cole isto na sua IA (Claude Code, Codex, Gemini CLI…)

> Leia o repositório https://github.com/inematds/artefatos-livres (o README e o CONTRATO.md). Depois me pergunte quais páginas, listas ou planilhas a minha equipe usa hoje por link (inclusive artifacts do Claude) e me diga, em linguagem simples: quais dariam para virar uma página do Artefatos Livres, onde rodar (no meu computador, numa VPS ou só como página estática) e o que eu perderia em relação ao Claude. Não instale nem mude nada antes do meu sim. Com o meu sim: baixe o kit, rode os testes, crie a primeira página a partir do modelo que fizer mais sentido, publique, suba o servidor e me mande o link para eu abrir.

**Usar sem instalar?** Não há versão online: a ideia é a página ficar com você. O mais perto é publicar só a página (sem dados compartilhados) numa hospedagem estática grátis.
**Onde baixar?** Não há instalador: [ZIP do kit](https://github.com/inematds/artefatos-livres/archive/refs/heads/main.zip) ou `git clone`.

---

# Instalação técnica

## Por que existe

Os Artifacts do Claude viraram um lugar de trabalho: página por link, versões, dados, comentários e, agora,
"instalar como app". Funciona bem, mas a página, os dados e quem pode abrir ficam na conta da Anthropic, e quem abre
precisa entrar no Claude. A própria central de ajuda da Anthropic diz: para uma ferramenta interna com backend,
publique na sua infraestrutura. É isso que este kit faz, no mesmo formato, com a fonte de verdade em arquivos seus.

## O que o kit faz × Artifacts do Claude

| Recurso | Artifacts do Claude | artefatos-livres |
|---|---|---|
| Página por link, privada por padrão | sim | sim (link com chave; sem chave = 403) |
| Versão nova no mesmo link | sim | sim (`/nome/` = última, `/nome/v/N/` = cada versão) |
| Instalar como app | beta; Mac e Windows; sem Linux, web e celular | PWA: Chrome/Edge em Windows, Mac, Linux, Android (precisa de HTTPS ou localhost) |
| Dados compartilhados (lista, inscrição) | sim | sim (SQLite no seu servidor) |
| Comentários na página | sim, e marcar o Claude para corrigir | sim (painel 💬); a correção você pede à IA que quiser |
| A página chama IA | sim, na cota de quem abre | opcional: qualquer comando (`claude -p`, `codex exec -`, `ollama run …`) na conta do dono |
| Conectores (Gmail, Slack, BigQuery…) | sim | **não**: a página só vê o próprio servidor |
| Modelos Docs/Slides/Sheets prontos | sim | não; há 3 modelos simples (tarefas, inscrições, em branco) |
| Quem abre precisa de conta | sim, no Claude | não; só o link |
| Sair levando tudo | exporta o conteúdo | `exportar`: HTML + dados em JSON e CSV, sem a chave |

## O processo, do início ao fim

| # | Passo | Comando | Quem |
|---|---|---|---|
| 1 | Criar a página a partir de um modelo | `python3 artefatos.py novo tarefas --titulo "Tarefas da equipe"` | 🧠 você |
| 2 | Escrever/ajustar o HTML (à mão ou pedindo a qualquer IA com o `CONTRATO.md`) | editar `paginas/tarefas/index.html` | 🧠 você / 🤖 IA |
| 3 | Publicar a versão | `python3 artefatos.py publicar tarefas -m "primeira"` | ⚙️ script |
| 4 | Subir o servidor | `python3 artefatos.py servir --porta 8787` | ⚙️ script |
| 5 | Pegar o link para mandar | `python3 artefatos.py link tarefas --base https://seu.dominio` | ⚙️ script |
| 6 | Mudou? Edite e publique de novo: o link não muda | `python3 artefatos.py publicar tarefas -m "prazo"` | 🧠 / ⚙️ |
| 7 | Ver as versões | `python3 artefatos.py versoes tarefas` | ⚙️ |
| 8 | (opcional) Ligar a IA da página | `LIVRE_IA_CMD='ollama run llama3.2' python3 artefatos.py servir` | 🧠 |
| 9 | Levar tudo embora | `python3 artefatos.py exportar tarefas --para ~/backup` | ⚙️ |

Requisito: Python 3.9+. Nada para instalar.

## Onde rodar

- **No seu PC, na rede da empresa**: `servir --host 0.0.0.0` e o link com o IP da máquina. Instalar como app pede HTTPS
  (ou `localhost`), então na rede local a página abre, mas o botão de instalar pode não aparecer.
- **Numa VPS sua com HTTPS**: Caddy na frente (`seu.dominio { reverse_proxy 127.0.0.1:8787 }`) e o servidor como serviço
  do systemd. Aí o link funciona para qualquer pessoa e o "instalar app" aparece no Chrome/Edge.
- **Só estático (GitHub Pages, qualquer hospedagem)**: suba a pasta `site/<nome>/`. A página abre e instala, mas
  os dados ficam no navegador de cada um (modo local) — serve para relatório, apresentação, painel de leitura.

## Segurança

- A chave do link é o acesso: quem tem o link abre e edita. Para tirar o acesso de alguém, troque a `chave` em
  `paginas/<nome>/pagina.json` e mande o link novo.
- O servidor só serve o que está em `site/`, limita o tamanho dos dados (256 KB por pedido, 64 KB por documento) e a
  IA (6 perguntas por minuto por pessoa). A página chama a IA pelo comando que **você** configurou; o texto vai pelo
  stdin, sem shell.
- Não é um sistema com login por pessoa nem papéis (admin/leitor). Precisa disso? Use uma ferramenta feita para isso.

## Testes

```bash
python3 -m unittest discover -s tests -v       # 18 testes: link, chave, versões, app, dados, comentários, IA, exportar
node tests/navegador.mjs "<link com chave>" .   # Chromium real: duas pessoas na mesma lista
```

## Arquivos

`artefatos.py` (CLI + servidor) · `nucleo/livre.js` (dados, comentários, IA, app) · `nucleo/sw.js` (offline) ·
`modelos/` (tarefas, inscrições, em branco) · `CONTRATO.md` (para qualquer IA) · `guia/` (página do projeto).

Licença MIT. Feito pela comunidade [INEMA.CLUB](https://inema.club).
