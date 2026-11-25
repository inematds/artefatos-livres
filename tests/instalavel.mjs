// O Chromium diz se a página (privada, aberta pelo link com chave) é instalável e se abre sem internet.
// Uso: PLAYWRIGHT_DIR=... node tests/instalavel.mjs "<link com chave>"
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_DIR || "playwright");
const link = process.argv[2];
const nav = await chromium.launch();
const ctx = await nav.newContext();
const p = await ctx.newPage();
await p.goto(link);
await p.evaluate(() => navigator.serviceWorker.ready);
await p.reload(); await p.waitForTimeout(800);   // 2ª visita: o service worker já controla e guardou a página
const cdp = await ctx.newCDPSession(p);
const man = await cdp.send("Page.getAppManifest");
const inst = await cdp.send("Page.getInstallabilityErrors");
console.log("manifest:", man.url, man.errors.length ? JSON.stringify(man.errors) : "sem erros", man.data ? "lido" : "VAZIO");
console.log("instalável:", inst.installabilityErrors.length ? JSON.stringify(inst.installabilityErrors) : "SIM");
await ctx.setOffline(true);
let off = "não abriu";
try { await p.reload({ timeout: 8000 }); off = (await p.title()) || "(sem título)"; } catch (e) { off = "falhou: " + e.message.split("\n")[0]; }
console.log("sem internet:", off);
await nav.close();
process.exit(inst.installabilityErrors.length || !man.data || off.startsWith("falhou") || off === "não abriu" ? 1 : 0);
