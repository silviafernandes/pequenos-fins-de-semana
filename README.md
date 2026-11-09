# Pequenos fins de semana ✳

Uma agenda pessoal para descobrir **atividades de bebés e crianças até aos 3 anos** nas proximidades dos **CTT dos 4 Caminhos, Senhora da Hora**. Dá prioridade às atividades **às 10:00**, que terminem antes da sesta das **12:00**, e às **inscrições da Biblioteca Municipal Florbela Espanca**.

O projeto contém um dashboard React (Vite), uma recolha conservadora de anúncios públicos em Python, histórico de alterações e uma automação **GitHub Actions → GitHub Pages**. O site fica numa **URL permanente** e os dados são republicados quando a tarefa agendada termina.

> **Estado do MVP:** a interface e a rotina automática estão implementadas. A descoberta automática é experimental e *não* consegue interpretar todas as páginas (por exemplo, Instagram, Google Forms fechado ou eventos montados inteiramente em JavaScript). Há ainda dados iniciais curados para novembro–dezembro de 2026. Um link encontrado **não é** prova de inscrições abertas. Antes de depender exclusivamente dos alertas, verifica os resultados das primeiras execuções.

Uma pré-visualização HTML **estática** do relatório anterior está incluída em `docs/preview-estatico-2026-11-09.html`; não tem as atualizações automáticas do projeto React.

## Configurar no GitHub e abrir no Codex

1. Cria um repositório chamado `pequenos-fins-de-semana` no GitHub (podes começar privado, mas verifica as condições do GitHub Pages para o teu plano). Descompacta este ZIP e coloca **todo o conteúdo da pasta** na raiz do repositório, incluindo `.github/workflows/site.yml`. Escolhe `main` como branch principal.
2. No GitHub, entra em **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Em **Actions**, abre `Atualizar e publicar a agenda` e seleciona **Run workflow**. Isto executa a primeira pesquisa, compila e publica a aplicação.
4. No resumo dessa execução, o link do `github-pages` é a URL permanente do teu dashboard (normalmente `https://UTILIZADOR.github.io/pequenos-fins-de-semana/`). Não precisas de criar novos ficheiros HTML todas as semanas.
5. Abre este repositório no **Codex** para continuar a desenvolver funcionalidades; começa pelo ficheiro [`CODEX_START_HERE.md`](CODEX_START_HERE.md).

**Não adiciones senhas, endereço residencial real ou dados pessoais de crianças ao repositório.** O ponto de origem é um estabelecimento público.

## Como atualiza

| Execução | Hora em Lisboa | Objetivo |
|---|---|---|
| Todos os dias | 09:13 | Anúncios e eventuais novos formulários |
| Sextas | 10:07, 10:37, 11:07, 13:07 e 16:07 | Foco nas bibliotecas e novas inscrições |
| Manual | A qualquer momento | `Actions → Run workflow` |

A agenda do browser consulta os JSON publicados de 10 em 10 minutos enquanto estiver aberta. O GitHub Actions **não executa garantidamente à hora exata**: pode atrasar-se, e não garante apanhar vagas que desaparecem em minutos. Mantém o lembrete pessoal para o dia **13 de novembro, às 10:00**, relativo ao evento *O Meu Primeiro Paninho*.

**Como funciona:** `scripts/update.py` lê a lista de fontes, visita páginas públicas e extrai links potencialmente relevantes. Só publica automaticamente uma atividade como *evento* se encontrar dados estruturados com **dia de fim de semana, horário, local e faixa etária**. Mesmo nesses casos, o estado da reserva permanece **por verificar**. Os novos anúncios sem detalhes suficientes aparecem numa secção separada intitulada **Novos anúncios**. O histórico guarda datas de abertura e links de formulário observados. Não faz login, ignora conteúdos privados e não contorna CAPTCHA.

## Receber alertas por Telegram (opcional)

Se quiseres avisos sobre **novos links de formulário** e **novas datas de abertura** detetadas nas páginas, sem teres de abrir o site:

1. Cria um bot com `@BotFather` no Telegram e obtém o token.
2. Abre uma conversa com o bot e envia uma mensagem para ele. Obtém o teu `chat_id` através da API do Telegram ou de uma ferramenta de confiança.
3. No GitHub, configura os **Actions secrets** `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` em **Settings → Secrets and variables → Actions**. Nunca os escrevas no código.
4. Executa manualmente o workflow. Na primeira execução ele cria uma base de comparação; os alertas só são enviados quando encontra alterações novas. Por defeito, não envia toda a lista de anúncios irrelevantes.

O envio de alertas é opcional; sem segredos a app e a recolha continuam a funcionar.

## Desenvolvimento local

```bash
npm install --no-audit --no-fund
npm run dev
# Em outro terminal:
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/update.py
```

Para fazer uma compilação de produção:

```bash
npm run build
```

## Ficheiros principais

- `src/App.jsx` e `src/styles.css` — dashboard responsivo em português, filtros, favoritos locais e exportação `.ics` dos eventos com horas conhecidas.
- `public/data/events.json` — eventos com informação suficiente para serem apresentados no calendário.
- `public/data/discoveries.json` — anúncios e links novos que exigem validação, incluindo erros por fonte.
- `public/data/history.json` — observações de inscrições e padrões, sem confundir hipóteses com regras.
- `public/data/watchlist.json` — fontes a monitorizar (bibliotecas, organizadores, ALLEGROW, Pequenos Planos, Pumpkin, etc.).
- `scripts/update.py` — motor de descoberta que corre no GitHub Actions.
- `.github/workflows/site.yml` — pesquisa, testes, atualização e publicação automática.
- `tests/test_update.py` — testes unitários básicos do extrator.

## Limitações e próximos passos

- **Não é uma plataforma de reservas.** O botão abre o formulário ou o website original. Só o organizador sabe se restam lugares.
- O motor inicial deteta mais facilmente páginas públicas com HTML e `schema.org/Event`; muitos sites não publicam esse formato. Adicionar extratores específicos para as fontes mais importantes é a evolução prioritária.
- Algumas fontes só mostram o conteúdo com JavaScript ou bloqueiam pedidos automáticos; elas surgirão com erro no histórico da recolha. Precisam de um adaptador autorizado (API/RSS) ou verificação humana.
- Distância máxima de 15 km é um critério editorial no MVP: **a geolocalização rigorosa e o tempo de viagem ainda não estão implementados**. Não assumir que todo o concelho de Gaia ou Maia cabe no raio.
- Favoritos são locais ao browser e não sincronizam entre dispositivos.
- Os horários de abertura conhecidos são **observações**. Uma sexta-feira às 10:00 não constitui prova de uma regra semanal.
- O GitHub Pages estático não contém um backend sempre ativo; os dados são gerados periodicamente pelo workflow e servidos como ficheiros estáticos.

## Segurança e privacidade

O site não recolhe nome, idade exata, email ou outros dados pessoais. Não armazena os dados dos formulários de inscrição. Evita publicar um verdadeiro endereço residencial; o ponto de referência dos CTT é suficiente.
