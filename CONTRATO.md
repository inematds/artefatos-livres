# Contrato da página — para você ou para qualquer IA

Cole este arquivo no Claude, Codex, Gemini, ChatGPT ou num modelo local e peça:
"crie/reescreva `paginas/<nome>/index.html` seguindo este contrato". O resultado roda igual em qualquer uma.

## Regras

1. **Um arquivo**: `paginas/<nome>/index.html`, HTML completo (`<!doctype html>`, `<meta charset>`, `<meta name="viewport">`).
   Imagens e CSS extras podem ficar na mesma pasta, com caminho relativo (`img/foto.png`).
2. **Sem chave nem login dentro do HTML.** Quem controla o acesso é o servidor (link com chave).
3. **Dados compartilhados só pelo `livre.js`** (o servidor injeta sozinho ao publicar). Espere ele ficar pronto:

```html
<script>
window.addEventListener("livre:pronto", async () => {
  const col = livre.db("pedidos");              // uma "tabela" por assunto
  livre.aoMudar(desenhar);                       // relê quando alguém muda (a cada 5 s)
  desenhar();
});
async function desenhar() {
  const docs = await livre.db("pedidos").listar();   // [{id, dados, autor, criado, atualizado}]
  // ... monta a tela com textContent (nunca innerHTML com texto de usuário)
}
</script>
```

| Função | O que faz |
|---|---|
| `livre.db(col).listar()` | todos os documentos da coleção |
| `livre.db(col).criar(dados, id?)` | novo documento (`dados` é objeto, até 64 KB) |
| `livre.db(col).trocar(id, dados)` | substitui (cria se não existir: bom para "um por pessoa") |
| `livre.db(col).juntar(id, dados)` | atualiza só os campos enviados |
| `livre.db(col).apagar(id)` | apaga |
| `livre.comentarios.listar()` / `.criar(texto, alvo?)` | comentários (o painel 💬 já vem pronto) |
| `livre.perguntar(texto)` | IA do dono do servidor, se ele ligou (`LIVRE_IA_CMD`); senão dá erro |
| `livre.nome` / `livre.definirNome(n)` | quem está usando (fica no navegador) |
| `livre.modo` | `"servidor"` (compartilhado) ou `"local"` (só neste navegador) |

4. **Sem servidor** (página aberta do disco ou no GitHub Pages) a mesma página funciona em modo local; avise o usuário
   se a página depende de ver os dados dos outros.
5. Atributos no `<body>`: `data-sem-comentarios` esconde o painel; `data-sem-aviso` esconde o aviso de modo local.
6. Visual: funciona em 360 px de largura, contraste nos dois temas (claro/escuro).

## Depois de escrever

```bash
python3 artefatos.py publicar <nome> -m "o que mudou"   # o link fixo passa a mostrar esta versão
```
