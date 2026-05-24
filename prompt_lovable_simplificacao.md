# PROMPT LOVABLE — Simplificação MESSAGING (consolidação beacon + notify)

> Produto MESSAGING consolida ex-BEACON (19 telas messaging-as-a-service multi-canal — email/SMS/push/WhatsApp) + ex-NOTIFY (legacy serviço notificações internas). ADR 0108. Path: `apps/beacon-ui/src/pages/messaging/`.
>
> Persona-alvo: **marketing/vendedor PME-BR + ops júnior + product manager + small business owner**. Quase ninguém é dev. Comprou para mandar WhatsApp promocional + email transacional + push de pedido pronto + lembrete SMS.

---

## CONTEXTO

Cognitive load atual: **72** (PIOR do Lote 5). Top 5 problemas sistêmicos:

1. **Zero CopilotFloating embedded** — comparar CONNECT (mesmo lote, gold standard 48) que tem CopilotFloating em TODAS as 12 telas. MESSAGING tem zero. Marketing/vendedor PME não consegue perguntar "como mando blast WhatsApp para 5k clientes sem virar Yellow?".
2. **Jargão técnico MASSIVO** — MJML, APNs, FCM, VAPID, IsolationForest, lawful_basis, DKIM, SPF, DMARC, BIMI, ARC, Anatel DND, Quality Rating Green/Yellow/Red, Tier 1k/10k/100k, BSP, WABA, Janela 24h, opt-in double, hard bounce, soft bounce, suppression list, webhook signature HMAC, idempotency key, MX records, throttle, list-unsubscribe, RFC 8058, GDPR Art. 6/7, LGPD Art. 7/8/9, lookalike, segment, RFM, retention curve, NPS, CTR, CAC. Marketing vê e fecha.
3. **Sem onboarding AI-first** — ausente tela `MessagingOnboarding.tsx`. CONNECT tem `ConnectAiFirstOnboarding.tsx` 1-prompt + 4 quick actions exemplar. MESSAGING joga vendedor direto em `BeaconOverview.tsx` com KPI grid técnico.
4. **Densidade extrema — 19 telas todas com tabela 7+col** — `BeaconDomains` (DKIM/SPF/DMARC mono), `BeaconMessages` (10col), `BeaconJourneys` (8col workflow), `BeaconAntispam` (9col com IsolationForest score), `BeaconSuppression` (lista compliance), `BeaconLgpd` (tabelas opt-in/opt-out/DSAR). Sem cards, sem gallery, sem kanban.
5. **Templates messaging multi-canal ausentes** — `BeaconTemplates.tsx` existe mas é catálogo técnico de templates Meta-approved + MJML. Falta galeria visual "Promoção Black Friday WhatsApp / Lembrete pagamento boleto / Abandono carrinho email / Novidade produto multi-canal" com preview real do que o cliente final recebe.

---

## TELAS A EXCLUIR

> Telas duplicadas (overlap com legacy notify) ou redundantes pós-consolidação.

| Tela | Razão | Destino |
|---|---|---|
| `BeaconWhatsapp.tsx` (se existe como tela separada) | **Overlap com rewire-CONNECT** (WhatsApp Business API dedicado). Manter WhatsApp em MESSAGING APENAS para transactional/notification simples (envio único OTP/lembrete) — conversação bot vai para CONNECT. Documentar separação clara. | Reduzir escopo a "WhatsApp transactional" + link "Para conversação bot/atendimento, use rewire-CONNECT". |
| Telas legacy notify (se existirem em apps/legacy/notify/src) | Notify legacy é serviço backend de notificações internas (rewire-cluster cross-product). Não tem UI de cliente. Manter apenas o backend service, UI cliente vive 100% em beacon-ui (MESSAGING). | Deletar UI legacy notify (se houver), manter notify como backend SDK consumido por outros produtos via API. |
| `BeaconPushApps.tsx` push notification SDK setup | Manter, mas mover para Modo Avancado. PME geral não usa push mobile apps — só apps com SDK iOS/Android. | Hide do menu Iniciante, visible em Avancado. |
| `BeaconChain.tsx` BLAKE3 audit chain | Ferramentaria compliance — overlap com rewire-AUDIT (que é o produto compliance centralizado). Manter visualização readonly em MESSAGING para "ver chain de mensagens enviadas", mas redirect ações ("Exportar prova") para rewire-AUDIT. | Refazer como readonly + link "Para compliance avançado (relatórios, auditor portal), use rewire-AUDIT". |

**Result: 19 telas → ~16 telas após consolidação e refacao escopo** (3 hidden/redirected).

---

## TELAS A REFAZER (P1 — 8 críticas) — aplicar 9 princípios canônicos

### 1. `MessagingOnboarding.tsx` (NOVA TELA — não existe hoje)

Criar onboarding AI-first análogo ao `ConnectAiFirstOnboarding.tsx`:

- Saudação "Olá! O que você quer mandar?" (informal).
- Textarea NOVA com prompt PT-BR: "Ex: 'Quero mandar promoção Black Friday no WhatsApp para 5k clientes' / 'Email de boas-vindas + sequência onboarding 5 emails' / 'SMS de OTP de login'".
- 4 quick actions ilustradas:
  - "Promoção WhatsApp/email" (Marketing blast)
  - "OTP/lembrete (transactional)" (Login + pagamento)
  - "Jornada onboarding" (Sequência multi-canal)
  - "Boas-vindas + retenção" (Triggers automáticos)
- AuthorityBanner: "Mesma arquitetura SendGrid/Mailchimp/OneSignal, sem lock-in, PT-BR-first, NF-e Lago."
- Checklist final: 5 itens (Conectar domínio email / Validar número SMS / Conectar WhatsApp BSP / Configurar opt-in LGPD / Mandar primeiro test).

### 2. `MessagingOverview.tsx` (ex-`BeaconOverview.tsx`)

- KPI grid técnico → cards visuais PT-BR coloquial:
  - "Mensagens enviadas hoje" (sparkline 30d)
  - "Taxa de entrega" (com tooltip "% que chegou no destinatário")
  - "Taxa de abertura" (email/push: %, WhatsApp: lido %)
  - "Conversões" (link CRM se conectado)
  - "Saúde dos canais" (4 dots verde/amarelo/vermelho: Email/SMS/Push/WhatsApp)
- Card "Próxima ação sugerida pela NOVA": "Você tem 187 carrinhos abandonados sem follow-up. Quer criar jornada de recuperação?"
- Empty state: "Sem mensagens enviadas? Comece pelo template Black Friday WhatsApp."
- **NOVA Copilot button** flutuante.

### 3. `MessagingTemplates.tsx` (ex-`BeaconTemplates.tsx`)

- **Galeria visual primeiro**, catálogo técnico depois.
- Cards categorizados:
  - Marketing (Promoção, Lançamento, Cupom, Newsletter)
  - Transactional (OTP, Boas-vindas, Pedido confirmado, Pagamento aprovado/recusado, Envio, Entrega)
  - Lifecycle (Abandono carrinho, Renovação assinatura, Pesquisa NPS, Aniversário cliente)
- Cada card: preview real do que cliente recebe (mockup celular para WhatsApp/SMS/push, browser para email) + "Clonar e personalizar" CTA.
- Modo Iniciante esconde MJML editor + Meta-approval flow (visible em Avancado).
- Library Rewire badge para 87 templates pré-aprovados Meta (igual CONNECT).
- Tooltip "Meta-approved" PT-BR: "WhatsApp Business exige aprovação prévia de templates promocionais. Os marcados 'Meta-approved' já passaram — você pode usar imediatamente."

### 4. `MessagingDomains.tsx` (ex-`BeaconDomains.tsx`)

- DKIM/SPF/DMARC mono strings → **wizard 4-step "Conectar seu domínio email"**:
  1. Domínio (input: `loja.com.br`)
  2. Auto-detect provedor DNS (Cloudflare/Registro.br/GoDaddy/Route53/Manual)
  3. **Auto-config se Cloudflare/Route53** (OAuth + create records), manual instructions se outro (copy-paste com botão "Copiar")
  4. Verify (DNS propagation check com retry automático cada 30s + status visual)
- Tooltips PT-BR:
  - DKIM: "assinatura digital do email — garante que veio mesmo do seu domínio"
  - SPF: "lista quais servidores podem enviar email pelo seu domínio"
  - DMARC: "política de o que fazer se DKIM/SPF falhar (rejeitar / quarentena / só monitorar)"
  - BIMI: "logo da marca aparece no Gmail/Outlook ao lado dos emails (autoridade visual)"
- Empty state: "Sem domínio? Use nosso subdomínio compartilhado @sandbox.rewire.com.br para testes (até 100 emails/dia grátis)."

### 5. `MessagingJourneys.tsx` (ex-`BeaconJourneys.tsx`)

- Tabela workflows 8col → **canvas visual no-code** (igual ASCEND workflows ou Zapier):
  - Trigger nodes (Form submit / API event / Tag added / Date / Manual)
  - Action nodes (Send WhatsApp / Send email / Send SMS / Send push / Wait X / Branch if-else / Update CRM / Tag user)
  - Connection drag-and-drop
- Galeria de templates jornadas: Abandono carrinho (3 etapas) / Boas-vindas (5 emails 7d) / Reativação inativos (carta + WhatsApp + push) / Onboarding SaaS / Lembrete pagamento boleto.
- NOVA inline: "Criar jornada a partir de objetivo" — textarea "Quero recuperar 30% dos carrinhos abandonados em 7d" → NOVA gera draft canvas editável.
- Modo Avancado: edição condições com JSON + filtros avancados RFM + lookalike.

### 6. `MessagingAntispam.tsx` (ex-`BeaconAntispam.tsx`)

- Tabela 9col com IsolationForest score → cards por risco com explicação PT-BR.
- Tooltip "IsolationForest": "algoritmo de IA que detecta padrões anormais (envios em massa sem opt-in, conteúdo spam-like, IPs suspeitos) — ajuda manter sua reputação de domínio limpa."
- LossAversion banner: "Sua reputação domínio caiu para 'medium'. 27% próximos emails podem cair em spam. Quer rodar diagnóstico NOVA?"
- CTA "Rodar diagnóstico antispam" → wizard (analisar conteúdo / verificar listas / verificar opt-in / verificar IPs / sugerir fixes).
- Modo Iniciante esconde technical scores, mostra apenas "Risco: Baixo/Médio/Alto" + 3 next-actions.

### 7. `MessagingLgpd.tsx` (ex-`BeaconLgpd.tsx`)

- 3 tabelas seguidas (opt-in / opt-out / DSAR) + Anatel DND CSV scroll longo → **dashboard "Saúde LGPD"** com:
  - Semáforo grande: Verde "Compliance OK" / Amarelo "Atenção" / Vermelho "Risco"
  - 4 KPIs: opt-ins ativos / opt-outs / DSAR vencendo / Anatel DND sync status
  - Drilldown opcional para cada (collapsible)
- Tooltips:
  - "LGPD Art. 18 (7 direitos)": "Direitos do titular: acesso, anonimização, portabilidade, exclusão, oposição, revogação consentimento, info uso. Tem 15d para responder."
  - "Anatel DND sync": "Lista 'Não Perturbe' da Anatel — diariamente comparamos com sua base SMS e bloqueamos números registrados. Multa Anatel até R$ 50M se ignorar."
  - "opt-in double": "Cliente confirma 2x (form + email confirmação) — proteção contra cadastros falsos e melhor reputação."
- Banner contextual escalonado por tier (vs banner hoje sempre "multa R$ 50M+"):
  - Tier Growth/Pro: "Mantenha opt-ins limpos para boa reputação."
  - Tier Scale: "LGPD ANPD fiscaliza, mantenha evidências."
  - Tier Enterprise: "Bacen 4.658 + multa até 2% faturamento."

### 8. `MessagingSuppression.tsx` (ex-`BeaconSuppression.tsx`)

- Lista compliance hard bounces / unsubscribes / complaints → cards com explicação.
- Tooltips:
  - "hard bounce": "email rejeitado permanentemente (endereço não existe) — remova da lista para não prejudicar reputação."
  - "soft bounce": "rejeitado temporariamente (caixa cheia, servidor fora) — tentamos de novo em 4h, 12h, 24h."
  - "complaint": "destinatário marcou seu email como spam — adicionado automaticamente à suppression."
- CTA "Limpar lista" → wizard "Vou remover X hard bounces, Y complaints, Z unsubs. Sua taxa de bounce vai cair de 4.2% para 1.8%. Confirma?".
- Botão "Import suppression CSV" (de outros provedores migrando) com mapping wizard.

---

## TELAS A AJUSTAR (P2 — 6 moderadas)

| Tela | Ajustes |
|---|---|
| `MessagingMessages.tsx` (ex-`BeaconMessages.tsx`) | Tabela 10col → cards expansíveis (1 row = 1 message com status icon + canal + dest + preview content + sent at + actions). Bulk actions (resend / suppress dest / export CSV). |
| `MessagingDeliverability.tsx` (ex-`BeaconDeliverability.tsx`) | KPIs delivery rate / open rate / click rate / bounce / complaint — adicionar comparação "vs média Rewire seu vertical (varejo: 24% open, você: 31% — top 15%)". Recomendações NOVA inline ("Sua hora de pico é 10h-12h em quartas. Que tal agendar a próxima campanha?"). |
| `MessagingSmsNumbers.tsx` (ex-`BeaconSmsNumbers.tsx`) | Wizard "Cadastrar SMS number BR" 4-step (operadora / DDD / 10/11 dígitos / verify SMS). Anatel DND opt-in toggle com explicação. Custo por SMS por operadora (Vivo/Claro/Tim/Oi) com hint NOVA "Para BR, Tim costuma ser melhor custo-benefício para volumes <10k/mês". |
| `MessagingPushApps.tsx` (ex-`BeaconPushApps.tsx`) | **Modo Avancado only** (PME geral não tem app mobile). Para quem usa: wizard SDK setup (iOS APNs cert / Android FCM key / Web VAPID). |
| `MessagingAnalytics.tsx` (ex-`BeaconAnalytics.tsx`) | Funnel visual + delivery curve + sentiment se WhatsApp. Comparações Rewire-vertical médias. NPS sparkline. Leaderboard agentes (se Connect conectado). Subtitle "ClickHouse rollups bilhões" → remover. |
| `MessagingWebhooks.tsx` (ex-`BeaconWebhooks.tsx`) | **Modo Avancado**. PME geral não usa webhooks. Para dev: cards endpoint + HMAC signature + retry policy + dead letter queue. |

---

## TELAS A MANTER (P3 — apenas refinamento)

| Tela | Observação |
|---|---|
| `MessagingTeam.tsx` (ex-`BeaconTeam.tsx`) | Roles + SSO + MFA. Refinar com roles PT-BR (Owner→Dono, etc.). |
| `MessagingApiKeys.tsx` (ex-`BeaconApiKeys.tsx`) | Modo Avancado. Manter scope colorido + rotate/revoke. |
| `MessagingBilling.tsx` (ex-`BeaconBilling.tsx`) | Lago + NF-e + per-channel pricing. Manter, traduzir MTD→"Mês corrente". |
| `MessagingSettings.tsx` (ex-`BeaconSettings.tsx`) | Cards categorizados. Refinar tooltips. |
| `MessagingChain.tsx` (ex-`BeaconChain.tsx`) | Readonly + redirect para rewire-AUDIT para compliance avançado. |

---

## TEMPLATES PRE-BUILT (10 verticais BR-PME)

Galeria visual em `MessagingOnboarding.tsx`, `MessagingTemplates.tsx` e `MessagingJourneys.tsx`:

1. **Promoção Black Friday WhatsApp** — template promocional Meta-approved + jornada 3 toques (preview → dia D → última hora) + segmentação RFM "compradores últimos 90d".
2. **Lembrete pagamento boleto** — SMS 3d antes vencimento + email + WhatsApp 1d antes + último dia. Multi-canal coordenado.
3. **Abandono carrinho e-commerce** — email 1h após + WhatsApp 24h + push 48h. Recupera 30% médio.
4. **Novidade produto multi-canal** — broadcast email + WhatsApp para opt-ins + push para app users.
5. **Boas-vindas SaaS B2B** — sequência 5 emails (D0, D2, D5, D10, D15) onboarding + ativação.
6. **OTP login transactional** — SMS BR + email fallback + push se app. 99.9% delivery SLA.
7. **Pesquisa NPS pós-compra** — email automático D7 após delivery + reminder D14 + ação se detrator.
8. **Renovação assinatura** — D-30, D-7, D-1, D+1 (graça). Email + WhatsApp. Reduz churn 18%.
9. **Reativação inativos** — clientes sem compra 90d → carta personalizada NOVA-gerada + cupom + multi-canal 3 toques.
10. **Aniversário cliente** — automation date-trigger + cupom personalizado + WhatsApp parabéns + email.

Cada template provisiona em 1 click: domínio configurado (se necessário) + segment audience + jornada workflow + templates content + analytics dashboard.

---

## ONBOARDING TOUR (5-7 steps, first-time)

1. **Boas-vindas** — "MESSAGING manda WhatsApp, email, SMS e push num produto só. Vamos configurar em 5min." Toggle Iniciante/Avancado (default Iniciante).
2. **O que você quer mandar?** — textarea NOVA + 4 quick actions (Promoção / Transactional / Jornada / Boas-vindas).
3. **Conectar canal primário** — wizard auto-detecta DNS para domínio email OU pula para SMS BR (cadastrar número) OU WhatsApp Business (link CONNECT). PME escolhe 1 canal para começar.
4. **Importar audiência** — CSV upload + auto-detect colunas (nome/email/telefone/tags) + LGPD opt-in confirmation (foi cadastrado com consentimento? Sim/Não/Verificar caso-a-caso).
5. **Escolher template** — galeria visual 10 templates + opção "Custom".
6. **Mandar primeiro test** — Para você mesmo (preview) → analytics em real-time + LossAversion banner se algum erro (DNS pendente, opt-in faltando, etc.).
7. **Jornada automatizada** — opcional: criar workflow básico (Abandono carrinho / Boas-vindas) → NOVA Copilot ajuda passo-a-passo.

Lib: `react-joyride`. Persist por user. Reabrir via Help menu.

---

## ESTRUTURA TÉCNICA (componentes compartilhados)

Criar em `src/components/messaging/simplification/`:

- `MessagingModeToggle.tsx` — Iniciante (Marketing PME) / Avancado (DevOps/Compliance) persistido.
- `MessagingWizardSteps.tsx` — wrapper para Conectar Domínio / Conectar SMS / Importar Audiência / Criar Template / Criar Jornada / Diagnóstico Antispam / Limpar Suppression.
- `MessagingTemplateGallery.tsx` — galeria 10 templates verticais com preview real (mockup celular para WhatsApp/SMS/push, browser email).
- `NovaCopilotButton.tsx` — botão flutuante em TODAS as telas (não existe hoje). Context-aware: detecta tela, sugere prompts ("Como mando blast WhatsApp sem virar Yellow?", "Por que email caiu em spam?", "Quanto custa enviar 5k SMS BR?").
- `EmptyStateEducational.tsx` — ilustração + 1-frase + CTA + 3 next-steps.
- `OnboardingTour.tsx` — react-joyride wrapper.
- `MessagingGlossaryTooltip.tsx` — wrap termos (`<Gloss term="DKIM">...</Gloss>`).
- `JourneyCanvasNoCode.tsx` — canvas drag-drop com triggers + actions (substituir tabela 8col por visual).
- `LgpdHealthDashboard.tsx` — semáforo + 4 KPIs + drilldown collapsible.
- `MessagePreviewMobile.tsx` — mockup celular WhatsApp/SMS/push para preview templates.

Templates: `src/content/messaging-templates.ts`.
Onboarding: `src/content/messaging-onboarding.ts`.
Glossário: `src/content/messaging-glossary.ts` (~70 termos: DKIM, SPF, DMARC, BIMI, MJML, APNs, FCM, VAPID, IsolationForest, hard bounce, soft bounce, complaint, suppression, Anatel DND, RFC 8058, list-unsubscribe, Quality Rating WhatsApp, Tier 1k/10k/100k, BSP, WABA, Janela 24h, opt-in double, LGPD Art. 18, lookalike, segment RFM, NPS, CTR, CAC, etc.).

---

## CHECKLIST POR TELA (do master)

- [ ] Toggle Iniciante (Marketing) / Avancado (DevOps/Compliance) no header
- [ ] Modo Iniciante = cards visuais PT-BR + NOVA destacada
- [ ] Modo Avancado = tabelas + technical details + MJML editor + JSON conditions
- [ ] NOVA Copilot button flutuante presente em TODAS telas (não existe hoje)
- [ ] Empty state educativo (ilustração + frase + CTA + 3 next-steps)
- [ ] Onboarding tour first-time
- [ ] Forms longos viraram wizards (Domínio / SMS / Template / Jornada / Diagnóstico / Suppression)
- [ ] Defaults inteligentes (Anatel DND ON BR, opt-in double ON LGPD, retry 3x exponential, etc.)
- [ ] Labels PT-BR coloquial (Modo Iniciante)
- [ ] Tooltips PT-BR em TODO jargão (DKIM/SPF/DMARC/BIMI/MJML/APNs/FCM/IsolationForest/etc.)
- [ ] Preview real mensagens (mockup celular + browser email)
- [ ] Comparações benchmark vertical Rewire (gamification)
- [ ] Loading + skeleton + error + sucesso states com next-step CTA
- [ ] Mobile-first (marketing PME acessa do celular)
- [ ] ARIA + keyboard nav + WCAG AA
- [ ] Lazy load + code splitting

---

## NOTAS FINAIS

- **Target = marketing PME não-dev** (vs Connect que é WhatsApp conversação bot — overlap parcial mas escopos diferentes).
- **Separação clara MESSAGING vs CONNECT** documentar:
  - MESSAGING: broadcasts, jornadas, transactional, OTP, multi-canal email/SMS/push/WhatsApp transactional.
  - CONNECT: conversação atendimento bot↔humano WhatsApp Business API dedicado.
- **NÃO descartar telas atuais** — viram Modo Avancado.
- **Cross-product refs** (pós ADR 0108): `rewire-connect` (WhatsApp atendimento dedicado), `rewire-audit` (compliance avançado), `rewire-pulse` (observability), `rewire-security`. `rewire-federation` invisible.
- **NÃO mencionar ADRs no user-facing**.
- **NÃO expor leaks técnicos** (ClickHouse, Redpanda, TimescaleDB) no Modo Iniciante.
- **Stack mantém**: React 19 + TS 5 + Vite 6 + Tailwind 4 + shadcn/ui + TanStack Query v5 + Zustand + react-hook-form + zod + react-joyride + framer-motion + i18next PT-BR default.
