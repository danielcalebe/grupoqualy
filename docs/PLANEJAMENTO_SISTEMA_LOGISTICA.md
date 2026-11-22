# PLANEJAMENTO DETALHADO — Sistema Web de Logística (Grupo Qualy)

| Campo | Valor |
|-------|-------|
| Projeto | Solução computacional para o setor de logística do Grupo Qualy |
| Documento | Planejamento técnico e executivo para implementação |
| Versão | 1.0 |
| Data | 2026-11-22 |
| Base documental | Etapa 3 — Projeto Eixo 1 - Grupo 2; Análise logística e rotas de coletas; Modelo C# v1.0; Mapa mental Etapa 1 |
| Stack aprovada | Python 3 / Flask / SQLite / Jinja2 + Bootstrap 5 / Leaflet (OSM) |
| Integrações Google | Estrutura pronta + modo mock (sem chave obrigatória na 1ª versão) |

---

## 1. Contexto e problema

### 1.1 A empresa

Grupo Qualy: compra, reciclagem e revenda de sucata de ferro. 21 funcionários, faturamento ≈ R$ 500.000/mês. Sistemas atuais: **DECA** (próprio, em evolução) e **Sygecom** (legado, sem integração). Comunicação operacional do setor logístico ainda depende de **Thunderbird (agenda) + prints no WhatsApp**.

### 1.2 O setor logístico — estado atual

- Frota: **3 caminhões** — 1 roll-on/roll-off, 2 garra; **3 motoristas internos**; **2 empresas parceiras** (carretas, coletas maiores).
- Volume: ~**6 coletas/dia** (garra) + **3–4/dia** (roll-on).
- Gatilho habitual de solicitação: carga **≥ 2.000 kg**.
- Tempo de execução: **garra ≈ 30 min**, **roll-on ≈ 20–25 min**.
- Planejamento: administradora monta rotas na agenda do Thunderbird; envia por print; motoristas terceirizados contatados diretamente.
- Rastreamento: aplicativo próprio + registro manual de saída/chegada na sala de administração.
- **Não há** sistema de horários definidos nem garantia de horário ao fornecedor.

### 1.3 Problemas a resolver (rastreio documental)

| ID | Problema | Origem na doc |
|----|----------|---------------|
| **P1** | Agendamento manual (Thunderbird + WhatsApp), muito retrabalho, baixa visibilidade | Análise logística; §5.1 Etapa 3 |
| **P2** | Rotas sem considerar distância, combustível, tempo ou capacidade | §2.4 |
| **P3** | Sem horários definidos/garantidos ao fornecedor | Análise logística |
| **P4** | Sem detecção de conflitos de veículo/motorista/janela | §5.3 |
| **P5** | Sem painel de status por cores nem mapa de pontos junto aos agendamentos | Análise logística; §5.4 |
| **P6** | Consulta de tíquete de descarregamento (vínculo à pesagem) ineficiente | Análise logística |
| **P7** | Programação diária por print; sem notificação estruturada | §5.1 |
| **P8** | Indicadores/alertas imprecisos (dashboard depende de WhatsApp/outras fontes) | §2.5 |

### 1.4 Requisitos funcionais de referência (doc §4.2.4)

- **RF-001** Integração de informações (estrutura de API/exportação pronta).
- **RF-002** Controle de usuários por função.
- **RF-003** Controle de acesso por perfil.
- **RF-004** Consulta de informações conforme permissões.
- **RF-005** Registro de operações (rastreabilidade/auditoria).

### 1.5 Requisitos não funcionais de referência (doc §4.2.5)

Segurança, disponibilidade, desempenho, confiabilidade, facilidade de uso, recuperação de dados, escalabilidade, manutenibilidade, auditoria.

---

## 2. Objetivos e metas

### 2.1 Objetivo geral

Entregar aplicação web que centralize o ciclo de coletas do setor de logística do Grupo Qualy — do agendamento à rotas, execução, tíquete, indicadores e alertas — reduzindo trabalho manual, conflitos e falhas de informação.

### 2.2 Metas mensuráveis

| Meta | Critério de aceite |
|------|--------------------|
| M1 | Agendar coleta com validação e sugestão de slots em conflito (≥ 90% dos fluxos de teste automatizados passando) |
| M2 | Gerar rota diária com agrupamento por bairro e ordem de visita otimizada (km ≤ baseline guloso simples nos testes) |
| M3 | Painel com ≥ 4 status coloridos e mapa com pontos do dia |
| M4 | Consulta por nº de tíquete retorna coleta + peso em ≤ 1 clique após login |
| M5 | KPIs do dia atualizados a cada mudança de status; ≥ 3 tipos de alerta ativos |
| M6 | Login + 5 perfis com permissões distintas; auditoria de alterações de status |

---

## 3. Escopo

### 3.1 In scope (v1)

1. Autenticação e perfis (RF-002, RF-003).
2. Cadastros: fornecedores, pontos de coleta, veículos, motoristas, empresas parceiras, disponibilidades.
3. Agendamento de coletas com validações, conflitos e sugestões.
4. Rotas diárias: agrupamento por bairro, ordenação, cálculo de tempo/km (mock), impressão/exportação da programação.
5. Painel operacional: kanban por cores, calendário do dia, mapa Leaflet.
6. Fluxo de status da coleta + histórico (RF-005).
7. Tíquete de descarregamento e consulta pública-interna por número.
8. Indicadores e motor de alertas.
9. Notificações internas (in-app); e-mail/WhatsApp apenas como estrutura mock.
10. Estrutura de integração Google Maps/Calendar com fallback mock.

### 3.2 Out of scope (v1)

- Substituir DECA/Sygecom por completo.
- Integração real com balança, NF-e, ERP financeiro (estoque/margem — outros setores).
- 2FA, SSO, firewall/infra de rede (escopo de infraestrutura da doc, separado).
- App mobile nativo; PWA pode ser futuro.
- Deploy em produção (documentar apenas).

### 3.3 Premissas

- Python ≥ 3.11; SQLite local; sem necessidade de Docker na v1.
- Coordenadas dos pontos: mock determinístico (ou geocoding se chave disponível).
- Usuários seed com senha provisória `Qualy@123` (dev) — trocar em produção.

---

## 4. Arquitetura

### 4.1 Diagrama lógico

```
┌─────────────────────────────────────────────────────────────┐
│                     Navegador (Jinja2 + Bootstrap + JS)     │
│   Painel │ Agendamento │ Rotas │ Cadastros │ Relatórios      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (sessão cookie)
┌───────────────────────────▼─────────────────────────────────┐
│  Flask (blueprints)                                         │
│  web/routes: auth, painel, coletas, rotas, cadastros, ...   │
├─────────────────────────────────────────────────────────────┤
│  services/   regras de negócio                              │
│  agendamento, rotas, indicadores, notificacoes,             │
│  estoque_pesagem, integrations/google_*                     │
├─────────────────────────────────────────────────────────────┤
│  algorithms/  conflitos, agrupamento, ordenacao_rota        │
├─────────────────────────────────────────────────────────────┤
│  core/       db, models, auth, seed                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │     SQLite      │
                   │  (arquivo .db)  │
                   └─────────────────┘
```

### 4.2 Convenções

- Código: nomes em inglês; mensagens/labels de UI em **português (pt-BR)**.
- Endpoints: rotas em inglês (`/collections/new`), textos pt-BR.
- IDs: INTEGER PRIMARY KEY AUTOINCREMENT; códigos de coleta: `COL-AAAA-XXXX` (ex.: `COL-2026-0001`).
- Timestamps: ISO-8601 em UTC armazenado; exibição em horário local.
- Pesos: INTEGER gramas ou REAL kg — **decisão: REAL kg** com 3 casas (balança).
- Dinheiro: REAL BRL com 2 casas (apenas se escopo financeiro entrar; v1 não calcula margem).

### 4.3 Estrutura de diretórios (alvo final)

```
grupo_qualy/
├── docs/
│   ├── PLANEJAMENTO_SISTEMA_LOGISTICA.md   ← este documento
│   └── ... (documentação original do projeto)
├── requirements.txt
├── config.py
├── app.py                 # factory create_app()
├── wsgi.py                # entrypoint gunicorn/werkzeug
├── README.md
├── core/
│   ├── __init__.py
│   ├── db.py              # engine SQLite, helpers de query
│   ├── schema.sql         # DDL completo
│   ├── models.py          # dataclasses / mapeamento de linhas
│   ├── auth.py            # hash, login_required, roles
│   └── seed.py            # dados iniciais
├── services/
│   ├── __init__.py
│   ├── agendamento.py
│   ├── rotas.py
│   ├── indicadores.py
│   ├── notificacoes.py
│   ├── estoque_pesagem.py
│   └── integrations/
│       ├── __init__.py
│       ├── google_maps.py
│       └── google_calendar.py
├── algorithms/
│   ├── __init__.py
│   ├── conflitos.py
│   ├── agrupamento.py
│   └── ordenacao_rota.py
├── web/
│   ├── __init__.py        # register_blueprints
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── painel.py
│   │   ├── coletas.py
│   │   ├── rotas.py
│   │   ├── cadastros.py
│   │   ├── tickets.py
│   │   └── relatorios.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/login.html
│   │   └── ...
│   └── static/
│       ├── css/app.css
│       └── js/...
├── data/
│   └── logistica.db       # (gitignore)
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_conflitos.py
    ├── test_agrupamento.py
    └── test_flows.py
```

---

## 5. Especificação do modelo de dados

### 5.1 Enumerações

| Enum | Valores |
|------|---------|
| `perfil_usuario` | `administradora`, `chefe_logistica`, `motorista`, `balanca`, `financeiro` |
| `tipo_veiculo` | `roll_on`, `garra`, `carreta_terceirizada` |
| `tipo_motorista` | `interno`, `terceirizado` |
| `status_coleta` | `agendada`, `em_andamento`, `concluida`, `cancelada`, `urgente`* |
| `origem_solicitacao` | `fornecedor_solicitou`, `logistica_contatou` |
| `canal_notificacao` | `sistema`, `email`, `whatsapp`, `telefone` |

\* Na doc `Urgente` é status; na implementação **`urgente` é flag booleana** na coleta, e o status segue o fluxo normal — evita estado que impede transição. O painel pinta urgentes com cor de destaque sobre o status atual.

### 5.2 Transições de status da coleta

```
agendada ──► em_andamento ──► concluida
   │              │
   └──────────────┴──► cancelada   (exige motivo)
```

- Transições válidas apenas para perfis: `administradora`, `chefe_logistica`, `motorista` (execução).
- `cancelada` exige `motivo_cancelamento` não vazio.
- Toda transição grava `historico_status` (RF-005).
- Ao concluir: opcionalmente vincular/gerar tíquete.

### 5.3 Tabelas (DDL resumido — completo em `core/schema.sql`)

**usuarios**
`id, nome, email UNIQUE, senha_hash, perfil, ativo, criado_em`

**fornecedores**
`id, razao_social, nome_fantasia, cnpj_cpf, telefone, email, frequente, ativo`

**pontos_coleta**
`id, fornecedor_id FK, nome, logradouro, numero, bairro, cidade, uf, cep, latitude, longitude, nome_responsavel, contato_responsavel, tipo_veiculo_padrao, peso_gatilho_kg, distancia_patio_km, tempo_deslocamento_minutos, observacoes, ativo`

**empresas_parceiras**
`id, razao_social, cnpj, telefone, email, ativo`

**veiculos**
`id, placa UNIQUE, descricao, tipo, capacidade_kg, tempo_execucao_padrao_minutos, identificador_rastreador, terceirizado, empresa_parceira_id FK NULL, ativo`

**motoristas**
`id, nome, cpf, cnh, telefone, email, tipo, empresa_parceira_id FK NULL, usuario_id FK NULL, ativo`

**disponibilidades_motorista**
`id, motorista_id FK, inicio, fim, disponivel, motivo`

**coletas**
`id, codigo UNIQUE, ponto_coleta_id FK, veiculo_id FK NULL, motorista_id FK NULL, criada_por_usuario_id FK, tipo_veiculo_necessario, origem, status, urgente, data_solicitacao, data_hora_prevista_inicio, data_hora_prevista_fim, data_hora_real_saida, data_hora_real_chegada, tempo_deslocamento_ida_minutos, tempo_deslocamento_volta_minutos, tempo_execucao_minutos, tempo_total_minutos, peso_estimado_kg, peso_real_kg, ordem_na_rota, rota_diaria_id FK NULL, observacoes, motivo_cancelamento, id_evento_agenda_externa, criado_em, atualizado_em`

**tickets_descarregamento**
`id, coleta_id FK UNIQUE, numero UNIQUE, pesagem_id NULL, peso_liquido_kg, data_hora_descarregamento`

**rotas_diarias**
`id, data, veiculo_id FK, motorista_id FK, elaborada_por_usuario_id FK, distancia_total_prevista_km, tempo_total_previsto_minutos, data_hora_envio_programacao`

**historico_status_coleta**
`id, coleta_id FK, status_anterior, status_novo, data_hora, usuario_id FK, observacao`

**notificacoes_coleta**
`id, coleta_id FK, motorista_id FK NULL, usuario_id FK NULL, canal, mensagem, data_hora_envio, lida`

**alertas**
`id, tipo, severidade (info|aviso|critico), mensagem, ref_tabela, ref_id, resolvido, criado_em, resolvido_em`

**audit_log**
`id, usuario_id FK NULL, acao, tabela, registro_id, detalhe_json, data_hora` — genérico (RF-005).

### 5.4 Índices

- `coletas(data_hora_prevista_inicio)`, `coletas(status)`, `coletas(codigo)`, `coletas(veiculo_id, data_hora_prevista_inicio)`
- `pontos_coleta(bairro)`, `pontos_coleta(fornecedor_id)`
- `historico_status_coleta(coleta_id)`
- `tickets_descarregamento(numero)`
- `alertas(resolvido)`

---

## 6. Regras de negócio

### RB-01 — Criação de coleta
- Campos obrigatórios: ponto de coleta, tipo de veículo necessário, data/hora prevista início, peso estimado (se informado ≥ 0), origem.
- Peso estimado opcional mas recomendado; se presente e `< peso_gatilho_kg` do ponto → **aviso** (não bloqueio), pois gatilho é indicativo.
- Sistema calcula: `tempo_execucao` padrão do tipo de veículo; `tempo_deslocamento_ida/volta` do ponto (ou mock Maps); `tempo_total = ida + execucao + volta`; `data_hora_prevista_fim = inicio + tempo_total`.
- Código gerado automaticamente sequencial por ano.

### RB-02 — Conflito de agendamento
- Conflito se existe coleta com status ∈ {agendada, em_andamento, urgente*} no **mesmo veículo** OU **mesmo motorista**, cuja janela `[inicio - ida, fim + volta]` sobreponha a janela da nova.
- Janela considerada: `[data_hora_prevista_inicio - ida_min, data_hora_prevista_fim]` (volta já embutida no fim conforme modelo).
- Motorista com `disponivel=false` no intervalo → bloqueio com motivo.
- Em conflito: resposta lista **sugestões** = próximos slots livres de ≥ 30 min no mesmo veículo/intervalo útil (06:00–18:00) nas próximas 72h.

### RB-03 — Alocação de veículo/motorista
- Obrigatória na confirmação da rota diária; opcional no agendamento (pode ser “a definir”).
- Veículo deve ter `tipo` compatível com `tipo_veiculo_necessario` da coleta (carreta terceirizada aceita qualquer tipo de demanda de parceira).
- Capacidade: soma de `peso_estimado_kg` das coletas do dia ≤ `capacidade_kg` (se informada) — **aviso** se exceder; **bloqueio** apenas se exceder por > 20%.

### RB-04 — Agrupamento e ordenação de rota
- Entrada: coletas do dia com status `agendada` de um veículo.
- Passo 1: agrupar por `bairro` (bucket).
- Passo 2: ordem dos bairros = menor distância acumulada a partir do pátio (mock: heurística por nome/índice).
- Passo 3: dentro do bairro, vizinho mais próximo a partir do ponto anterior (pátio = origem).
- Passo 4: 2-opt (≤ 20 iterações ou melhora < 1%) com custo = tempo deslocamento.
- Passo 5: atribuir `ordem_na_rota` e recalcular horários previstos encadeados (partida pátio 07:00 padrão, configurável).
- Respeitar janela de execução do veículo; se estourar expediente → alerta na rota.

### RB-05 — Execução
- `em_andamento` grava `data_hora_real_saida` (auto no primeiro status).
- `concluida` grava `data_hora_real_chegada`; permite informar `peso_real_kg`; divergência `|peso_real - estimado| > 15%` → gera **alerta**.
- Obrigatório coleta concluída gerar **tíquete** (número `TQ-AAAA-XXXX`); pesagem_id opcional (mock numérico).

### RB-06 — Cancelamento
- Exige motivo; notifica motorista se já alocado; libera janela automaticamente (efeito RB-02).

### RB-07 — Indicadores (recalculados sob demanda + ao mutar status)
| KPI | Fórmula |
|-----|---------|
| Coletas do dia | COUNT(status ≠ cancelada) |
| Kg transportados | SUM(peso_real ?? peso_estimado) concluídas |
| Tempo médio de coleta | AVG(tempo_execucao) concluídas |
| Atrasadas | concluída com chegada > fim previsto + 15 min |
| Ocupação da frota | veículos com ≥1 coleta / veículos ativos |
| Pendentes de tíquete | concluídas sem ticket |

### RB-08 — Alertas (regras v1)
| Tipo | Condição | Severidade |
|------|----------|------------|
| `atraso` | coleta em_andamento com chegada prevista + 15 min | aviso |
| `sem_rota` | veículo ativo sem coletas em dia útil | info |
| `peso_divergente` | \|real − estimado\|/estimado > 15% | critico |
| `fornecedor_inativo` | ponto frequente sem coleta há 30 dias | info |
| `capacidade` | soma estimada > 100% capacidade | critico |

### RB-09 — Permissões (matriz)

| Ação | administradora | chefe_logistica | motorista | balanca | financeiro |
|------|:--------------:|:---------------:|:---------:|:-------:|:----------:|
| Login / ver painel | ✓ | ✓ | ✓ | ✓ | ✓ |
| CRUD cadastros | ✓ | ✓ | — | — | — |
| Agendar/editar coleta | ✓ | ✓ | — | — | — |
| Gerar rota diária | ✓ | ✓ | — | — | — |
| Alterar status (execução) | ✓ | ✓ | ✓ (suas) | — | — |
| Cancelar coleta | ✓ | ✓ | — | — | — |
| Consultar tíquete | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ver indicadores | ✓ | ✓ | ✓ (restrito) | ✓ | ✓ |
| Resolver alertas | ✓ | ✓ | — | ✓ | — |
| Gerenciar usuários | ✓ | — | — | — | — |

---

## 7. Especificação de algoritmos

### 7.1 `algorithms/conflitos.py`

```
function janela(coleta):  # minutos desde meia-noite ou datetime
    return [inicio_previsto - ida, fim_previsto]

function detectar_conflitos(veiculo_id, motorista_id, nova_janela, data):
    conflitos = []
    for c in coletas_do_dia(veiculo_id ∪ motorista_id, status ativas):
        if sobrepor(janela(c), nova_janela):
            conflitos.append(c)
    for d in disponibilidades_bloqueantes(motorista_id, nova_janela):
        conflitos.append(bloqueio(d))
    return conflitos

function sugerir_slots(veiculo_id, motorista_id, data, duracao_min, horizonte_dias=3):
    # varre 06:00–18:00 em passos de 30 min; retorna primeiros 5 livres
```

- Complexidade: O(n) por chamada (n = coletas do dia) — suficiente para ~10/dia.
- Testes: sobreposição parcial, adjacente sem sobrepor (fim == início ⇒ **sem** conflito), bloqueio de folga, veículo livre/motorista ocupado.

### 7.2 `algorithms/agrupamento.py`

```
function agrupar_por_bairro(pontos, patio):
    buckets = dict(bairro → [pontos])
    # ordena bairros por distância mock(patio, bairro_centroide)
    return [(bairro, pontos) para bairro em ordem]
```

### 7.3 `algorithms/ordenacao_rota.py`

```
function ordenar(pontos_do_dia, patio):
    grupos = agrupar_por_bairro(...)
    rota = []
    atual = patio
    for grupo in grupos:
        while grupo não vazio:
            prox = argmin(dist(atual, p) for p in grupo)
            rota.append(prox); atual = prox; grupo.remove(prox)
    rota = two_opt(rota, patio, max_iter=20)
    return rota
```

### 7.4 `services/integrations/google_maps.py`

- `get_distancia_tempo(origem, destino)` → `(km, minutos)`.
- Se `GOOGLE_MAPS_API_KEY` ausente → **mock**: distância Euclidiana × fator 1.3 (ruas), velocidade 35 km/h urbano; cache em memória.
- API real: Directions/Distance Matrix (estrutura documentada no docstring).

### 7.5 `services/integrations/google_calendar.py`

- `criar_evento(coleta)` → dict; sem credenciais → gera `id_evento_agenda_externa = MOCK-<coleta_id>` e registra em log.
- Estrutura de OAuth/Service Account documentada para produção.

---

## 8. Especificação de interface (páginas)

| Rota | Título | Perfis | Conteúdo principal |
|------|--------|--------|--------------------|
| `GET/POST /login` | Login | todos | email, senha |
| `GET /` | Painel | todos | KPIs do dia, alertas, link rápido |
| `GET /painel/operacao` | Operação do dia | logística, admin, motorista | kanban + calendário + mapa |
| `GET /coletas`, `GET/POST /coletas/nova` | Coletas | logística, admin | lista + formulário com conflitos |
| `GET /coletas/<id>` | Detalhe | acima + motorista | status, histórico, tíquete |
| `GET /rotas`, `GET/POST /rotas/gerar` | Rotas | logística, admin | lista do dia + gerar/ordenar |
| `GET /rotas/<id>/imprimir` | Programação | logística, admin | layout limpo para PDF/impressão |
| `GET/POST /cadastros/*` | Cadastros | logística, admin | fornecedores, pontos, veículos, motoristas |
| `GET /tickets/busca` | Tíquete | todos | busca por número |
| `GET /relatorios` | Relatórios | logística, admin, financeiro | KPIs período, export CSV |
| `GET/POST /usuarios` | Usuários | admin | CRUD (F1+) |
| `GET /alertas` | Alertas | logística, admin, balança | lista e resolver |

**Elementos de UI obrigatórios**
- Cores de status: agendada `#0d6efd`, em_andamento `#fd7e14`, concluída `#198754`, cancelada `#6c757d`; urgente borda `#dc3545`.
- Kanban com drag-não obrigatório (botões de status suficientes na v1).
- Mapa Leaflet com marcadores filtrados por dia/status.
- Flash messages pt-BR; validação inline.
- Responsividade mínima 768px (usada em telas da balança/pátio).

---

## 9. API interna (JSON — usada pelo painel e futura integração)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/health` | healthcheck |
| GET | `/api/coletas?data=YYYY-MM-DD` | lista do dia |
| POST | `/api/coletas` | cria (mesma RB do form) |
| POST | `/api/coletas/<id>/status` | transição {status, observacao} |
| GET | `/api/coletas/<id>/conflitos` | dry-run de conflitos |
| POST | `/api/rotas/gerar` | gera rota {data, veiculo_id} |
| GET | `/api/indicadores?de=&ate=` | KPIs |
| GET | `/api/tickets/<numero>` | consulta tíquete |
| GET | `/api/alertas` | lista alertas abertos |

- Auth: sessão cookie (mesmo do form); status 401/403 conforme perfil.
- Erros: `{ "erro": "...", "campo": "..." }` com HTTP adequado.

---

## 10. Segurança

1. Senhas: `werkzeug.security.generate_password_hash` (pbkdf2/scrypt).
2. Sessão: cookie `HttpOnly`, `SameSite=Lax`; `SECRET_KEY` via variável de ambiente em produção.
3. CSRF: token Flask nos POSTs de formulário (implementar em F2 com `flask-wtf` ou manual).
4. Consultas SQL parametrizadas (sem string concat).
5. Perfis aplicados em decorator `@require(...)` em cada rota (matriz RB-09).
6. Auditoria: `audit_log` em criar/editar/cancelar/status.
7. Sem exposição de `senha_hash` em templates/API.
8. Rate-limit básico no login (F2): falhas > 5 → bloqueio temporário em memória.

---

## 11. Plano de fases e tarefas

### F1 — Fundação (EXECUTADA — 2026-11-22)
- [x] Documento de planejamento
- [x] `requirements.txt`, `config.py`, `app.py` (factory), `wsgi.py`
- [x] `core/schema.sql` completo + `core/db.py` (init, get, helpers)
- [x] `core/models.py` (mapeamentos)
- [x] `core/auth.py` (hash, decorators de sessão/perfil)
- [x] `core/seed.py` (5 usuários, 3 veículos, 3 motoristas, exemplo de ponto)
- [x] Blueprints `auth` + rota `/` protegida mínima
- [x] Templates `base.html`, `auth/login.html`, `painel/home.html` provisório
- [x] Testes: `test_auth.py` — **9 passed**
- [x] README mínimo (como rodar)

### F2 — Cadastros
- CRUD fornecedores, pontos de coleta (com lat/lng mock), veículos, motoristas, disponibilidades, usuários (admin).
- CSRF; paginação simples; busca por nome/bairro.

### F3 — Agendamento
- Formulário + services + `algorithms/conflitos.py` + sugestões de slot + API dry-run.
- Detalhe da coleta com histórico.

### F4 — Rotas diárias
- `agrupamento.py`, `ordenacao_rota.py`, `services/rotas.py`, impressão da programação, envio mock.

### F5 — Painel e execução
- Kanban, mapa Leaflet, calendário do dia, transições de status, tíquete + consulta.

### F6 — Indicadores e alertas
- `services/indicadores.py`, `services/notificacoes.py`, motor de alertas, página de alertas.

### F7 — Integrações, testes e acabamento
- Google mock/real documentado, testes de fluxo, CSV de relatórios, polimento, README final.

---

## 12. Plano de testes

| Suíte | Fase | Cobre |
|-------|------|-------|
| `test_auth.py` | F1 | login/logout, senha inválida, rota protegida, matriz de perfis |
| `test_cadastros.py` | F2 | CRUD, validações, permissões |
| `test_conflitos.py` | F3 | sobreposição, sugestões, bloqueio folga |
| `test_agrupamento.py` | F4 | bairros, ordem, capacidade |
| `test_flows.py` | F5–F6 | agendar → rota → status → tíquete → KPI/alerta |
| Manual | F7 | checklist das metas M1–M6 |

Comando: `python -m pytest -q` na raiz do projeto.

---

## 13. Riscos e mitigação

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Dados de geolocalização sem API | rotas menos precisas | mock determinístico; pluggável para Directions API |
| Escopo de outros setores tentar entrar | atraso | out of scope rígido; estoque/margem = outro projeto |
| Senhas fracas no seed | segurança | aviso no README; força troca em produção |
| SQLite concorrência | média | poucos usuários (21); WAL mode; upgrade path PostgreSQL documentado |
| Modelo C# ≠ implementação | divergência | este doc é fonte; C# é referência de atributos |

---

## 14. Critérios de aceite gerais (entrega do projeto)

1. Usuário logado por perfil vê apenas o que a matriz RB-09 permite.
2. É possível agendar coleta, receber sugestão em conflito e gerar rota do dia.
3. Painel mostra status por cores e mapa com pontos do dia.
4. Tíquete consultável por número com dados de pesagem.
5. ≥ 5 KPIs e ≥ 3 alertas funcionando.
6. Suíte de testes automatizados verde.
7. README com instruções de instalação e execução.

---

## 15. Como executar (alvo — será consolidado no README)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py          # cria DB + seed automático se vazio
# abrir http://127.0.0.1:5000
python -m pytest -q    # testes
```

**Usuários seed (dev):**

| Perfil | Email | Senha |
|--------|-------|-------|
| administradora | admin@grupoqualy.com.br | Qualy@123 |
| chefe_logistica | logistica@grupoqualy.com.br | Qualy@123 |
| motorista | motorista@grupoqualy.com.br | Qualy@123 |
| balanca | balanca@grupoqualy.com.br | Qualy@123 |
| financeiro | financeiro@grupoqualy.com.br | Qualy@123 |

---

*Fim do planejamento. Início da F1 conforme seção 11.*
