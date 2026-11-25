# Artefatos Livres

[![Artefatos Livres: tus páginas por enlace, sin depender de Claude](guia/assets/banner-es.jpg)](https://inematds.github.io/artefatos-livres/guia/es/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## Qué es

Quieres la practicidad de mandar un enlace y que todos usen la misma página, sin entregar a tu equipo y tus datos a una sola empresa. Artefatos Livres es un kit gratuito que hace, en un computador o servidor tuyo, lo que hacen los Artifacts de Claude: página abierta por enlace (privada por defecto), versión nueva en la misma dirección, instalar como aplicación, lista y registro compartidos y comentarios. Cualquier IA escribe la página (Claude, Codex, Gemini o un modelo en tu PC), o tú mismo. Para usarlo, basta un computador con Python y pedirle a tu IA que lo instale.

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/artefatos-livres/guia/es/**

## Cómo empezar: pega esto en tu IA (Claude Code, Codex, Gemini CLI…)

> Lee el repositorio https://github.com/inematds/artefatos-livres (el README y el CONTRATO.md). Después pregúntame qué páginas, listas u hojas de cálculo usa hoy mi equipo por enlace (incluidos los artifacts de Claude) y dime, en lenguaje sencillo: cuáles podrían convertirse en una página de Artefatos Livres, dónde ejecutarlo (en mi computador, en una VPS o solo como página estática) y qué perdería en comparación con Claude. No instales ni cambies nada antes de mi sí. Con mi sí: descarga el kit, ejecuta las pruebas, crea la primera página a partir del modelo que tenga más sentido, publícala, levanta el servidor y mándame el enlace para que lo abra.

**¿Usarlo sin instalar?** No hay versión en línea: la idea es que la página se quede contigo. Lo más cercano es publicar solo la página (sin datos compartidos) en un alojamiento estático gratuito.
**¿Dónde descargarlo?** No hay instalador: [ZIP del kit](https://github.com/inematds/artefatos-livres/archive/refs/heads/main.zip) o `git clone`.

---

# Instalación técnica

## Por qué existe

Los Artifacts de Claude se convirtieron en un lugar de trabajo: página por enlace, versiones, datos, comentarios y, ahora,
"instalar como app". Funciona bien, pero la página, los datos y quién puede abrirla quedan en la cuenta de Anthropic: sin cuenta, la parte con IA de la página no funciona,
y los documentos y hojas solo se abren iniciando sesión. El propio centro de ayuda de Anthropic dice: para una herramienta interna con backend,
publícala en tu infraestructura. Eso es lo que hace este kit, en el mismo formato, con la fuente de verdad en archivos tuyos.

## Qué hace el kit × Artifacts de Claude

| Recurso | Artifacts de Claude | artefatos-livres |
|---|---|---|
| Página por enlace, privada por defecto | sí | sí (enlace con clave; sin clave = 403) |
| Versión nueva en el mismo enlace | sí | sí (`/nome/` = la última, `/nome/v/N/` = cada versión) |
| Instalar como app | beta; Mac y Windows; sin Linux, web ni celular | PWA: Chrome/Edge en Windows, Mac, Linux, Android (necesita HTTPS o localhost) |
| Datos compartidos (lista, inscripción) | sí | sí (SQLite en tu servidor) |
| Comentarios en la página | sí, y mencionar a Claude para que corrija | sí (panel 💬); la corrección se la pides a la IA que quieras |
| La página llama a una IA | sí, con la cuota de quien abre | opcional: cualquier comando (`claude -p`, `codex exec -`, `ollama run …`) en la cuenta del dueño |
| Conectores (Gmail, Slack, BigQuery…) | sí | **no**: la página solo ve su propio servidor |
| Modelos Docs/Slides/Sheets listos | sí | no; hay 3 modelos simples (tareas, inscripciones, en blanco) |
| Quien abre necesita cuenta | la mayoría se abre sin iniciar sesión; docs/hojas y la parte con IA o conectores piden cuenta | no; solo el enlace (la IA, si está activada, corre en la cuenta del dueño) |
| Irse llevándose todo | exporta el contenido | `exportar`: HTML + datos en JSON y CSV, sin la clave |

## El proceso, de principio a fin

| # | Paso | Comando | Quién |
|---|---|---|---|
| 1 | Crear la página a partir de un modelo | `python3 artefatos.py novo tarefas --titulo "Tarefas da equipe"` | 🧠 tú |
| 2 | Escribir/ajustar el HTML (a mano o pidiéndoselo a cualquier IA con el `CONTRATO.md`) | editar `paginas/tarefas/index.html` | 🧠 tú / 🤖 IA |
| 3 | Publicar la versión | `python3 artefatos.py publicar tarefas -m "primeira"` | ⚙️ script |
| 4 | Levantar el servidor | `python3 artefatos.py servir --porta 8787` | ⚙️ script |
| 5 | Obtener el enlace para enviar | `python3 artefatos.py link tarefas --base https://seu.dominio` | ⚙️ script |
| 6 | ¿Cambió algo? Edita y publica de nuevo: el enlace no cambia | `python3 artefatos.py publicar tarefas -m "prazo"` | 🧠 / ⚙️ |
| 7 | Ver las versiones | `python3 artefatos.py versoes tarefas` | ⚙️ |
| 8 | (opcional) Conectar la IA de la página | `LIVRE_IA_CMD='ollama run llama3.2' python3 artefatos.py servir` | 🧠 |
| 9 | Llevarte todo | `python3 artefatos.py exportar tarefas --para ~/backup` | ⚙️ |

Requisito: Python 3.9+. Nada que instalar.

## Dónde ejecutarlo

- **En tu PC, en la red de la empresa**: `servir --host 0.0.0.0` y el enlace con la IP de la máquina. Instalar como app pide HTTPS
  (o `localhost`), así que en la red local la página abre, pero el botón de instalar puede no aparecer.
- **En una VPS tuya con HTTPS**: Caddy al frente (`seu.dominio { reverse_proxy 127.0.0.1:8787 }`) y el servidor como servicio
  de systemd. Así el enlace funciona para cualquier persona y el "instalar app" aparece en Chrome/Edge.
- **Solo estático (GitHub Pages, cualquier alojamiento)**: sube la carpeta `site/<nome>/`. La página abre y se instala, pero
  los datos quedan en el navegador de cada uno (modo local): sirve para informe, presentación, panel de lectura.

## Seguridad

- La clave del enlace es el acceso: quien tiene el enlace abre y edita. Para quitarle el acceso a alguien, cambia la `chave` en
  `paginas/<nome>/pagina.json` y manda el enlace nuevo.
- El servidor solo sirve lo que está en `site/`, limita el tamaño de los datos (256 KB por solicitud, 64 KB por documento) y la
  IA (6 preguntas por minuto por persona). La página llama a la IA mediante el comando que **tú** configuraste; el texto va por
  stdin, sin shell.
- No es un sistema con login por persona ni roles (admin/lector). ¿Necesitas eso? Usa una herramienta hecha para eso.

## Pruebas

```bash
python3 -m unittest discover -s tests -v       # 18 pruebas: enlace, clave, versiones, app, datos, comentarios, IA, exportar
node tests/navegador.mjs "<enlace con clave>" .   # Chromium real: dos personas en la misma lista
```

## Archivos

`artefatos.py` (CLI + servidor) · `nucleo/livre.js` (datos, comentarios, IA, app) · `nucleo/sw.js` (offline) ·
`modelos/` (tareas, inscripciones, en blanco) · `CONTRATO.md` (para cualquier IA) · `guia/` (página del proyecto).

Licencia MIT. Hecho por la comunidad [INEMA.CLUB](https://inema.club).
