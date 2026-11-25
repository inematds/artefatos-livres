// Teste no navegador real (Playwright/Chromium): duas pessoas abrem o mesmo link, uma adiciona,
// a outra vê; comentário aparece; o Chrome reconhece o manifest (instalável).
// Uso: node tests/navegador.mjs <link-com-chave> <pasta-para-prints>
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const caminho = process.env.PLAYWRIGHT_DIR || "playwright";
const { chromium } = require(caminho);

const [link, saida = "."] = process.argv.slice(2);
if (!link) { console.error("uso: node tests/navegador.mjs <link> [pasta]"); process.exit(2); }
const nav = await chromium.launch();
const ana = await (await nav.newContext({ viewport: { width: 420, height: 800 } })).newPage();
const bia = await (await nav.newContext({ viewport: { width: 420, height: 800 } })).newPage();
const erros = [];
for (const p of [ana, bia]) p.on("pageerror", (e) => erros.push(String(e)));

await ana.goto(link); await bia.goto(link);
await ana.waitForFunction(() => window.livre && window.livre.modo === "servidor");
await bia.waitForFunction(() => window.livre && window.livre.modo === "servidor");
await ana.evaluate(() => livre.definirNome("Ana"));
const item = "Mandar proposta " + Date.now();
await ana.fill("#nova", item); await ana.click("form button");
await bia.waitForSelector(`text=${item}`, { timeout: 12000 });
console.log("ok: Bia viu a tarefa que a Ana criou");
await bia.locator("li", { hasText: item }).locator("input[type=checkbox]").check();
await ana.waitForSelector("li.feita", { timeout: 12000 });
console.log("ok: Ana viu a tarefa marcada pela Bia");

await bia.click(".livre-bt");
await bia.fill(".livre-pn .livre-nome", "Bia");
await bia.fill(".livre-pn textarea", "Pode pôr prazo em cada tarefa?");
await bia.click(".livre-enviar");
await ana.click(".livre-bt");
await ana.waitForSelector("text=Pode pôr prazo", { timeout: 12000 });
console.log("ok: comentário da Bia apareceu para a Ana");

const manifest = await ana.evaluate(async () => {
  const href = document.querySelector('link[rel="manifest"]').href;
  return (await fetch(href)).json();
});
const sw = await ana.evaluate(async () => !!(await navigator.serviceWorker.getRegistration()));
console.log("ok: manifest", manifest.display, "| service worker registrado:", sw);
await ana.screenshot({ path: `${saida}/ana.png` });
await bia.screenshot({ path: `${saida}/bia.png` });
await nav.close();
if (erros.length) { console.error("ERROS JS:", erros); process.exit(1); }
if (!sw || manifest.display !== "standalone") process.exit(1);
console.log("TUDO OK");
