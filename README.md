# Sistema Web de Logística — Grupo Qualy

Aplicação web (Python/Flask) para o setor de logística do Grupo Qualy: agendamento de coletas com detecção de conflitos, rotas diárias otimizadas, painel operacional com mapa, tíquete de descarregamento, indicadores e alertas.

## Documentação

- **[PLANEJAMENTO_SISTEMA_LOGISTICA.md](docs/PLANEJAMENTO_SISTEMA_LOGISTICA.md)** — planejamento completo, requisitos, modelo de dados, regras de negócio, algoritmos e fases.

## Stack

- Python 3.11+ / Flask / SQLite
- Jinja2 + Bootstrap 5
- Leaflet + OpenStreetMap (mapa do dia)
- Integrações Google Maps/Calendar em modo mock (estrutura pronta para produção)

## Como executar

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>.

### Variáveis de ambiente (opcionais)

| Variável | Uso |
|----------|-----|
| `SECRET_KEY` | Chave de sessão (obrigatória em produção) |
| `GOOGLE_MAPS_API_KEY` | Distance Matrix real; sem chave → mock Euclidiano |
| `GOOGLE_CALENDAR_CREDENTIALS` | JSON service account; sem valor → evento `MOCK-<id>` |
| `FLASK_ENV` | `production` desativa debug |

### Usuários de desenvolvimento (seed)

| Perfil | E-mail | Senha |
|--------|--------|-------|
| administradora | admin@grupoqualy.com.br | Qualy@123 |
| chefe_logistica | logistica@grupoqualy.com.br | Qualy@123 |
| motorista | motorista@grupoqualy.com.br | Qualy@123 |
| balanca | balanca@grupoqualy.com.br | Qualy@123 |
| financeiro | financeiro@grupoqualy.com.br | Qualy@123 |

## Testes

```bash
python -m pytest -q
```

## Status das fases

| Fase | Escopo | Status |
|------|--------|--------|
| F1 | Fundação: Flask, SQLite, auth, painel | **concluída** |
| F2 | Cadastros (fornecedores, pontos, veículos, motoristas, usuários) | **concluída** |
| F3 | Agendamento + conflitos + sugestões de slot | **concluída** |
| F4 | Rotas diárias (agrupamento, vizinho mais próximo, 2-opt, impressão) | **concluída** |
| F5 | Painel kanban + mapa Leaflet + status + tíquete | **concluída** |
| F6 | Indicadores (KPIs) + motor de alertas + notificações + CSV | **concluída** |
| F7 | Integrações Google mock, testes de fluxo, acabamento | **concluída** |

## Funcionalidades (RB)

- **P1** Agendamento com conflito de veículo/motorista + sugestões de horário
- **P2** Rotas agrupadas por bairro, ordenadas (vizinho mais próximo + 2-opt)
- **P3** Painel de operação com kanban por cores e mapa Leaflet
- **P4** Transições de status com histórico e permissões
- **P5** Tíquete `TQ-AAAA-XXXX` gerado ao concluir + consulta
- **P6** Indicadores: ≥ 6 KPIs (coletas, kg, tempo médio, atrasadas, frota, tickets)
- **P7** Alertas: atraso, sem rota, peso divergente, capacidade, fornecedor inativo
- **P8** RB-09 matriz de permissões + CSRF + senhas com hash

## API JSON

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | healthcheck |
| GET | `/api/indicadores?de=&ate=` | KPIs |
| GET | `/api/alertas` | alertas abertos |
| GET | `/api/coletas?data=` | coletas do dia |
| GET | `/api/tickets/<numero>` | consulta tíquete |

Auth: sessão cookie (mesmo do form).

## Estrutura

Ver seção 4.3 do documento de planejamento.
