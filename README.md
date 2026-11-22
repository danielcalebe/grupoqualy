# Sistema Web de Logística — Grupo Qualy

Aplicação web (Python/Flask) para o setor de logística do Grupo Qualy: agendamento de coletas com detecção de conflitos, rotas diárias otimizadas, painel operacional com mapa, tíquete de descarregamento, indicadores e alertas.

## Documentação

- **[PLANEJAMENTO_SISTEMA_LOGISTICA.md](docs/PLANEJAMENTO_SISTEMA_LOGISTICA.md)** — planejamento completo, requisitos, modelo de dados, regras de negócio, algoritmos e fases.

## Stack

- Python 3.11+ / Flask / SQLite
- Jinja2 + Bootstrap 5
- Leaflet + OpenStreetMap (mapa — F5)
- Integrações Google Maps/Calendar em modo mock (estrutura pronta)

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
| F2 | Cadastros | pendente |
| F3 | Agendamento + conflitos | pendente |
| F4 | Rotas diárias | pendente |
| F5 | Painel kanban + mapa + tíquete | pendente |
| F6 | Indicadores + alertas | pendente |
| F7 | Integrações Google, testes e acabamento | pendente |

## Estrutura

Ver seção 4.3 do documento de planejamento.
