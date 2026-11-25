# FALHAS

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-11-25 | Página privada caía no "modo local": o cookie da chave tinha Path=/<nome>/ e não chegava a /api/<nome>/ (só o teste no navegador real pegou; os 17 testes unitários passavam) | Path=/ no cookie + teste unitário do cookie na API | prompt |
| 2026-11-25 | Autor de tarefa trocava para quem editou ("anônimo" ao marcar) | gravar() mantém o autor original; teste | prompt |
| 2026-11-25 | Página privada não instalava como app: o navegador busca o manifest sem cookie (403); o teste com fetch() dentro da página mascarava | crossorigin="use-credentials" no manifest + ícone público + tests/instalavel.mjs (CDP) | prompt |
