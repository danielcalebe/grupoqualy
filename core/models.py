"""Mapeamento de entidades (dataclasses) — espelha o modelo C# da Etapa 3."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ======================= ENUMS (constantes) =======================

PERFIS = ("administradora", "chefe_logistica", "motorista", "balanca", "financeiro")
TIPOS_VEICULO = ("roll_on", "garra", "carreta_terceirizada")
TIPOS_MOTORISTA = ("interno", "terceirizado")
STATUS_COLETA = ("agendada", "em_andamento", "concluida", "cancelada")
ORIGENS_SOLICITACAO = ("fornecedor_solicitou", "logistica_contatou")
CANAIS_NOTIFICACAO = ("sistema", "email", "whatsapp", "telefone")

# Transições permitidas (RB-02/planejamento §5.2)
TRANSICOES_STATUS: dict[str, tuple[str, ...]] = {
    "agendada": ("em_andamento", "cancelada"),
    "em_andamento": ("concluida", "cancelada"),
    "concluida": (),
    "cancelada": (),
}

# Permissões por perfil (RB-09) — ações relevantes
PERMISSOES: dict[str, set[str]] = {
    "administradora": {
        "ver_painel", "cadastros", "agendar", "gerar_rota", "alterar_status",
        "cancelar", "ver_tique", "ver_indicadores", "resolver_alertas",
        "gerenciar_usuarios", "ver_mapa",
    },
    "chefe_logistica": {
        "ver_painel", "cadastros", "agendar", "gerar_rota", "alterar_status",
        "cancelar", "ver_tique", "ver_indicadores", "resolver_alertas",
        "ver_mapa",
    },
    "motorista": {
        "ver_painel", "alterar_status", "ver_tique", "ver_indicadores_restrito",
        "ver_mapa",
    },
    "balanca": {
        "ver_painel", "ver_tique", "ver_indicadores", "resolver_alertas",
    },
    "financeiro": {
        "ver_painel", "ver_tique", "ver_indicadores",
    },
}


# ======================= MODELOS =======================

@dataclass
class Usuario:
    id: int
    nome: str
    email: str
    senha_hash: str
    perfil: str
    ativo: bool = True
    criado_em: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Usuario":
        return cls(
            id=row["id"],
            nome=row["nome"],
            email=row["email"],
            senha_hash=row["senha_hash"],
            perfil=row["perfil"],
            ativo=bool(row.get("ativo", 1)),
            criado_em=row.get("criado_em", ""),
        )

    def pode(self, acao: str) -> bool:
        return acao in PERMISSOES.get(self.perfil, set())


@dataclass
class Fornecedor:
    id: int
    razao_social: str
    nome_fantasia: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    frequente: bool = False
    ativo: bool = True


@dataclass
class PontoColeta:
    id: int
    fornecedor_id: int
    nome: str
    logradouro: str
    bairro: str
    cidade: str
    uf: str
    nome_responsavel: str
    numero: Optional[str] = None
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contato_responsavel: Optional[str] = None
    tipo_veiculo_padrao: str = "garra"
    peso_gatilho_kg: Optional[float] = None
    distancia_patio_km: Optional[int] = None
    tempo_deslocamento_minutos: Optional[int] = None
    observacoes: Optional[str] = None
    ativo: bool = True


@dataclass
class Veiculo:
    id: int
    placa: str
    tipo: str
    tempo_execucao_padrao_minutos: int = 30
    descricao: Optional[str] = None
    capacidade_kg: Optional[float] = None
    identificador_rastreador: Optional[str] = None
    terceirizado: bool = False
    empresa_parceira_id: Optional[int] = None
    ativo: bool = True


@dataclass
class Motorista:
    id: int
    nome: str
    tipo: str = "interno"
    cpf: Optional[str] = None
    cnh: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    empresa_parceira_id: Optional[int] = None
    usuario_id: Optional[int] = None
    ativo: bool = True


@dataclass
class Coleta:
    id: int
    codigo: str
    ponto_coleta_id: int
    criada_por_usuario_id: int
    tipo_veiculo_necessario: str
    origem: str
    status: str
    data_hora_prevista_inicio: str
    data_hora_prevista_fim: str
    urgente: bool = False
    veiculo_id: Optional[int] = None
    motorista_id: Optional[int] = None
    data_solicitacao: str = ""
    data_hora_real_saida: Optional[str] = None
    data_hora_real_chegada: Optional[str] = None
    tempo_deslocamento_ida_minutos: int = 0
    tempo_deslocamento_volta_minutos: int = 0
    tempo_execucao_minutos: int = 0
    tempo_total_minutos: int = 0
    peso_estimado_kg: Optional[float] = None
    peso_real_kg: Optional[float] = None
    ordem_na_rota: Optional[int] = None
    rota_diaria_id: Optional[int] = None
    observacoes: Optional[str] = None
    motivo_cancelamento: Optional[str] = None
    id_evento_agenda_externa: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Coleta":
        data = dict(row)
        data["urgente"] = bool(data.get("urgente", 0))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class TicketDescarregamento:
    id: int
    coleta_id: int
    numero: str
    pesagem_id: Optional[int] = None
    peso_liquido_kg: Optional[float] = None
    data_hora_descarregamento: Optional[str] = None


@dataclass
class Alerta:
    id: int
    tipo: str
    severidade: str
    mensagem: str
    ref_tabela: Optional[str] = None
    ref_id: Optional[int] = None
    resolvido: bool = False
    criado_em: str = ""
    resolvido_em: Optional[str] = None
