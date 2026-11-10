# Pequenos fins de semana ✳

Uma agenda pessoal para descobrir **atividades de bebés e crianças com menos de 3 anos** nas proximidades dos **CTT dos 4 Caminhos, Senhora da Hora**. Dá prioridade às atividades **às 10:00**, que terminem antes da sesta das **12:00**, e às **inscrições da Biblioteca Municipal Florbela Espanca**.

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

**Como funciona:** `scripts/update.py` lê a lista de fontes, visita páginas públicas e extrai links potencialmente relevantes. Só publica automaticamente uma atividade como *evento* se encontrar dados estruturados ou um adaptador oficial que valide **dia de fim de semana, horário, local e faixa etária**. Mesmo nesses casos, o estado da reserva permanece **por verificar**. Os novos anúncios sem detalhes suficientes aparecem numa secção separada intitulada **Novos anúncios**. O histórico guarda datas de abertura e links de formulário observados. Não faz login, ignora conteúdos privados e não contorna CAPTCHA.

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
- O motor deteta páginas públicas com `schema.org/Event` e inclui um adaptador para a Florbela Espanca; muitos outros sites precisam de um adaptador próprio. Adicionar extratores específicos para as fontes mais importantes é a evolução prioritária.
- Algumas fontes só mostram o conteúdo com JavaScript ou bloqueiam pedidos automáticos; elas surgirão com erro no histórico da recolha. Precisam de um adaptador autorizado (API/RSS) ou verificação humana.
- O limite de 15 km é calculado em linha reta a partir dos CTT 4 Caminhos, com coordenadas verificadas do estabelecimento e de cada recinto. Locais sem coordenadas verificadas ficam pendentes. Não se calculam tempos nem distâncias de condução.
- Favoritos são locais ao browser e não sincronizam entre dispositivos.
- Os horários de abertura conhecidos são **observações**. Uma sexta-feira às 10:00 não constitui prova de uma regra semanal.
- O GitHub Pages estático não contém um backend sempre ativo; os dados são gerados periodicamente pelo workflow e servidos como ficheiros estáticos.

## Segurança e privacidade

O site não recolhe nome, idade exata, email ou outros dados pessoais. Não armazena os dados dos formulários de inscrição. Evita publicar um verdadeiro endereço residencial; o ponto de referência dos CTT é suficiente.

## Melhorias de monitorização (novembro de 2026)

- O adaptador de Matosinhos lê data, hora e idade na página oficial de cada evento da Florbela Espanca. Ignora a meia-noite usada como marcador no calendário do site e não inventa a hora de fim.
- As páginas de eventos já conhecidos voltam a ser consultadas, mesmo quando deixam de aparecer na página inicial. Os formulários são extraídos do conteúdo do evento, incluindo URLs publicadas como texto.
- Uma única data explícita de abertura, com hora, pode atualizar a ficha e o histórico quando a página corresponde exatamente a uma única sessão. Nunca transforma a sessão em “inscrições abertas”. Várias sessões ou datas na mesma página exigem validação humana.
- A recolha verifica `robots.txt`, respeita exclusões e regista erros das páginas e formulários. Se o acesso ao formulário não for permitido, mantém a evidência anterior e assinala a limitação; não contorna o bloqueio.
- O painel mostra o último acesso bem-sucedido e falhas por fonte. Uma página acessível sem anúncios extraídos não prova que não existam atividades.
- O filtro “Inscrições a abrir esta semana” considera aberturas futuras até domingo, em Lisboa, e mostra também sessões cuja hora de fim ainda é desconhecida. Os filtros de idade abrangem 0–36 meses. Um local desconhecido deixa de ser apresentado automaticamente como interior.
- Cada publicação em `main` executa a recolha antes de publicar, além dos agendamentos existentes. Publicações de código não enviam Telegram; execuções manuais/agendadas mantêm os alertas opcionais configurados. Pull requests executam testes e compilação sem publicar.

Validação adicional do frontend:

```bash
npm ci
npx playwright install chromium
npm run build
npm run test:browser
```

O teste de browser utiliza dados fictícios identificados no próprio teste, uma data fixa e um servidor local; não faz reservas nem envia notificações. A fixture de Matosinhos é um excerto do HTML público, com URL e data de recolha no ficheiro.

Continuam por fazer: adaptadores específicos para ALLEGROW e outras fontes, validação da entrega de Telegram com credenciais configuradas e expansão do catálogo de recintos com coordenadas verificadas.

## Critério de idade: menores de 3 anos

A idade mínima tem de ser **inferior a 36 meses**. “A partir dos 3 anos”, “3+”, “3–10 anos” e “36–48 meses” são excluídos, incluindo dos novos anúncios. Intervalos como “6–36 meses” e “2–6 anos” incluem crianças menores de 3 anos e podem ser apresentados. Anúncios sem faixa etária explícita ficam fora do painel até haver evidência no título, no evento estruturado ou no adaptador oficial. A etiqueta “por validar” refere-se aos restantes detalhes; não permite ignorar a faixa etária. As mesmas regras são aplicadas novamente aos dados antigos em cada recolha.

## Knock-Knock Family Club

Incluído nas fontes prioritárias através do [calendário oficial](https://www.knock-knock.pt/calendario), com ligação para o perfil de Instagram indicado pelo identificador no site oficial. A leitura de Instagram não é automática e pode ser bloqueada. O espaço admite 0–5 anos segundo as regras oficiais, mas isso não confirma a idade de cada workshop. Não se criam sessões sem data, hora e evidência etária específica. Na verificação de 9 de novembro de 2026, o calendário público não tinha ocorrências nas seis semanas seguintes.

## Verificação de sessões e raio de 15 km

- O ponto de origem é a loja CTT da Rua Quatro Caminhos 134, Senhora da Hora, confirmada pela morada oficial dos CTT e pelo ponto do estabelecimento no mapa. O cálculo é Haversine, em **linha reta**, com comparação antes de arredondar. Não representa um percurso de carro.
- `public/data/venues.json` contém recintos identificados de forma exata, coordenadas, URL de proveniência e data de verificação. Os nomes não são substituídos pelo centro de uma cidade ou de uma rua. Um local desconhecido ou ambíguo aguarda verificação. Coordenadas: © OpenStreetMap contributors (ODbL), e pontos de estabelecimentos consultados no Waze, com ligações específicas em cada registo.
- Uma sessão precisa de data futura de fim de semana, hora explícita, faixa etária que admita menores de 36 meses, recinto identificado no raio e evidência recente na fonte original. O estado da reserva continua separado: formulário ou data de abertura não provam vagas.
- Os adaptadores da Oficina Josefina e Casa da Música leem datas e idades dos blocos correspondentes à atividade, sem misturar workshops na mesma página. O PaPI usa os horários e a duração da página da sessão e o ano explícito do programa oficial do festival, que liga essa sessão. Horas de fim não publicadas continuam desconhecidas.
- Cada sessão tem identidade própria, incluindo título, recinto, data e hora. Duas sessões no mesmo dia não são fundidas. Quando uma consulta bem-sucedida já não confirma a sessão, a evidência anterior é retirada. Uma falha de acesso preserva a última evidência explícita até 48 horas; depois, a sessão deixa de aparecer.
- `events.json` separa `events`, `pendingEvents` e `excludedEvents`. `discoveries.json` separa anúncios elegíveis de `pendingDiscoveries`. Os candidatos são mantidos para diagnóstico e novas consultas, mas só aparecem no painel quando a sessão concreta e a distância estão verificadas. Uma menção etária num agregador não é suficiente.
- Ao adicionar um novo recinto, registar primeiro as coordenadas do estabelecimento, a proveniência e os aliases exatos. Não aceitar automaticamente o primeiro resultado de uma pesquisa geográfica.
