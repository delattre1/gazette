# Apresentar o Gazette

Texto para o Mauricio. Copia, adapta o tom. Não lê em voz de robô.

## Links (usa em todo post)

| O quê | URL |
| --- | --- |
| Site | https://get-gazette.vercel.app |
| Repo | https://github.com/MAUXII/gazette |
| Index | https://aiworthusing.com/agent-index/gazette |

Clone + mint + `docker compose up --build -d`

> `gazette.vercel.app` e `gazete.vercel.app` já estavam ocupados na Vercel. Produção: **get-gazette.vercel.app**.

O placar conta **install** (container + linha Plow) e **tokens**. Like e RT não contam. Grupo no seu número = 1 install. Cada amigo que sobe o Docker na máquina **dele** = +1.

---

## O que falta (prioridade zero)

Só isso importa até 16/09. O resto é bonus.

| # | Feito? | O quê | Quando |
| --- | --- | --- | --- |
| 1 | ☐ | **Seu install no telefone.** Container rodando, setup fechado, PNG da manhã chegando no cron (ou `print today's paper` hoje pra validar). | Hoje / amanhã cedo |
| 2 | ☐ | **Vídeo 40-60s.** Plano 1 ou 3 abaixo. Corta loading. Cartão final: repo ou site. | Antes do post grande |
| 3 | ☐ | **Verified no Index.** Botão "Get my agent verified" em https://aiworthusing.com/agent-index/gazette | A partir de 14/09 |
| 4 | ☐ | **Post no Discord** (canal hackathon): foto da **sua** edição + clone. Texto: seção 1 abaixo. | 14/09 ou quando tiver vídeo |
| 5 | ☐ | **Post no X** (opcional no mesmo dia): mesma foto + link do site ou repo. | Junto com 4 |
| 6 | ☐ | **DM Dan** (danedelattre): uma frase. Gazette = jornal Karen, pede one-click no Plow quando existir. Sem implorar voto. | 14/09 |
| 7 | ☐ | **2-3 DMs** pra quem já manja (Auditbert, Caio, quem reagiu no canal): texto seção 2. Pede **install**, não like. | Esta semana |

**Já feito (não refaz):** repo público, Index, reporter, landing no ar, três faces, README.

**Não faz agora:** print Latch/Mac, STR, segundo projeto, feature thread com quem instalou.

---

## Quem manda mensagem, com o quê

| Pessoa / lugar | O quê mandar | Texto |
| --- | --- | --- |
| Discord geral | Post público | Seção **1. Curto** |
| Dev que já manja | DM | Seção **2. Pro Auditbert** |
| Amigo com Docker | DM direta | Seção **3. Pedido direto** |
| Dan (organizador) | DM curta | "Gazette is the installable Karen morning paper (PNG on Plow). Repo + site below. When one-click ships, I'd love Gazette on it." + links |
| Quem pergunta Life Assistant | Resposta rápida | Seção **4** |
| Depois que alguém instalou | Obrigado + horário do cron | Seção **6**. Pede screenshot do PNG deles. |

---

# Parte 1: roteiro do vídeo

Grava a tela. 40-60 segundos. Sem narrar "então tipo". Uma frase na boca, o resto é o que aparece.

Corte no Premiere/CapCut: qualquer spinner maior que 2s, acelera 4× ou corta para o PNG já na conversa.

## Antes de gravar (não entra no vídeo)

1. `reset` no Gazette, confirma, espera a resposta de perfil apagado.
2. Anota o número da linha (Spruce / +1 650…).
3. Fecha outras bolhas. Fundo limpo. Não mostra `plow-credentials`.
4. Cartão final: `get-gazette.vercel.app` ou `github.com/MAUXII/gazette`.

## Plano 1: o produto

| Tempo | Tela | Você faz | Fala (se quiser) |
| --- | --- | --- | --- |
| 0-3s | iMessage, lista de conversas | Dedo no lápis, nova conversa | |
| 3-8s | Campo do número | Cola o número, enter | "A line is just a number." |
| 8-12s | Chat vazio | Digita `hi`, envia | |
| 12-25s | Resposta do Gazette | Ele pede city, topics, GitHub, horário | "Four things. Then it prints." |
| 25-35s | Sua resposta **já digitada** (cola) | `São Paulo, AI agents and Formula 1, no github, deliver at 7` | |
| 35s-PNG | Spinner | **Corta ou acelera.** | |
| último 8s | Foto Planet, zoom no meio | Pinça na foto | "Your morning paper. As a picture." |

## Plano 2: perfil já configurado

1. Abre o chat que já existe.
2. `print today's paper`
3. Corta o loading.
4. Zoom na página.
5. Mesmo cartão final.

## Plano 3: 15s para Discord (story)

Só a foto chegando. Sem setup. Último frame: site ou clone.

## O que cortar sempre

- Gateway shutting down
- Você corrigindo inglês
- Ele falando que é Gazette vs Spruce
- Settings da Plow
- Terminal, Docker, este chat

## Legenda pronta (Discord / X)

This morning's paper, as a picture.

https://get-gazette.vercel.app  
Clone, mint, compose up: https://github.com/MAUXII/gazette

---

# Parte 2: textos prontos

## 1. Curto (canal geral / #projetos)

Gazette é um jornal da manhã. Você instala, escolhe cidade e uns assuntos, e todo dia chega **uma página de jornal como foto** no iMessage.

Não é newsletter. Não é resumo no chat. É a primeira página, de verdade. Planet colorido por padrão.

Tô no Hermes Hackathon (AI Worth Using × Plow). O que conta é gente instalando, não like.

Se você tem Docker: clone, `plow-agents mint`, `compose up`, manda um hi no número novo. Me manda o print da **sua** primeira página.

https://get-gazette.vercel.app  
https://github.com/MAUXII/gazette

## 2. Pro Auditbert / Caio / quem já manja de agente

Vocês já viram agente que fala. Esse imprime.

Hermes no Docker, linha Plow, zero key de modelo na sua máquina. Cron de manhã: gather (script) → o modelo só escreve o `edition.json` → Pillow renderiza A4 → `MEDIA:` no telefone.

Três faces (Times, Planet, Herald). Default é Planet color. MIT.

Hackathon: verified a partir de 14/09, submit 16/09 17h BRT, snapshot 22/09. Métrica é install + tokens no Agent Index.

Se puderem subir um container cada um e me mandarem o PNG, isso é o que move o placar.

https://get-gazette.vercel.app  
https://github.com/MAUXII/gazette  
https://aiworthusing.com/agent-index/gazette

## 3. Pedido direto (DM)

Fala. Tô com um agente no hackathon da Plow/Hermes: jornal matinal que chega como foto.

Preciso de gente que **instale**, não que dê moral. Docker + uma linha Plow. 10 minutos se o mint colaborar.

Quando a primeira página chegar no seu celular, me manda o print.

https://github.com/MAUXII/gazette

## 4. Se alguém perguntar "e o Life Assistant / a geladeira?"

Life Assistant é a casa inteira no Mac/Pi. Gazette é uma folha no telefone. Windows serve. Sem Latch.

The Plow Times imprime no Mac. A gente manda o PNG. Mesma ideia, outro objeto.

## 5. O que NÃO falar

- "É tipo o ChatGPT com jornal."
- "Apoiem o projeto" sem o clone.
- Pedir star no GitHub como se fosse a métrica.
- Prometer geladeira / kiosk / impressora automática essa semana.

## 6. Depois que eles instalarem

Pede o print. Confere se o Index subiu um user. Um "obrigado" e o horário que o jornal deles cai. Não abre thread de feature.
