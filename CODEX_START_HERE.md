# Tarefa para o Codex — próximos passos

Estás a trabalhar numa aplicação real chamada **Pequenos fins de semana**. O objetivo é monitorizar atividades para crianças dos 0 aos 3 anos, até ~15 km dos CTT dos 4 Caminhos na Senhora da Hora (Porto/Matosinhos/Maia/parte de Gaia), sobretudo 09:30–10:30, e com prioridade às inscrições das bibliotecas.

## Primeiro pedido ao Codex

1. Inspeciona e executa os testes existentes (`python -m unittest discover -s tests -v`). Instala dependências (`npm install --no-audit --no-fund`) e verifica `npm run build`. Corrige eventuais erros; não elimines funcionalidades nem inventes eventos.
2. Liga o repositório ao GitHub Pages via o workflow `.github/workflows/site.yml`, confirma a implantação e partilha a URL permanente.
3. Executa manualmente a recolha. Consulta logs de cada fonte em `public/data/discoveries.json` para distinguir sites acessíveis, bloqueados e sites com JavaScript.
4. Prioriza um **adaptador fiável para a Biblioteca Municipal Florbela Espanca** que acompanhe o site oficial, publicações de inscrição e formulários, e grave hora e dia de abertura quando explicitamente publicados. Depois cria adaptadores para Oficina Josefina e ALLEGROW. Usa sempre URLs originais e só diz que há vagas quando o organizador confirma.
5. Acrescenta testes com snapshots HTML reais permitidos, respeitando robots.txt, termos de uso, rate limits, privacidade e sem contornar autenticação/CAPTCHA.
6. Melhora o dashboard com um filtro “inscrições a abrir esta semana”, indicador de frescura por fonte e exclusão de eventos muito longe dos 4 Caminhos após geocodificação fiável.
7. Mantém o português de Portugal, o visual editorial leve e o filtro de sesta (preferir sessões acabadas até 11:30).

## Regras de integridade

- A **publicação de um formulário não confirma** inscrições abertas; uma data anunciada pode já ter passado.
- Não inferir horários ou idade por recorrência de eventos anteriores.
- Não importar qualquer anúncio como evento confirmado sem fonte, data, hora, local, faixa etária adequada e sinalização de incerteza na disponibilidade.
- Preferir fontes originais às agregadoras. Não inventar tempos de condução.
- Nunca colocar chaves do Telegram, identidade pessoal ou dados das crianças num repositório público.
- O GitHub Actions é periódico e sujeito a atrasos; não prometer notificações exatamente às 10:00.
