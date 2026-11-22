"""Dados iniciais (seed) — executa uma única vez se o banco estiver vazio."""
from __future__ import annotations

from core.auth import hash_senha
from core.db import Database

SENHA_DEV = "Qualy@123"

USUARIOS_SEED = [
    ("Administradora", "admin@grupoqualy.com.br", "administradora"),
    ("Chefe de Logística", "logistica@grupoqualy.com.br", "chefe_logistica"),
    ("Motorista Pátio", "motorista@grupoqualy.com.br", "motorista"),
    ("Operador de Balança", "balanca@grupoqualy.com.br", "balanca"),
    ("Financeiro", "financeiro@grupoqualy.com.br", "financeiro"),
]


def banco_vazio(database: Database) -> bool:
    row = database.query_one("SELECT COUNT(*) AS n FROM usuarios")
    return bool(row and row["n"] == 0)


def executar_seed(database: Database | None = None) -> bool:
    """Popula dados mínimos. Retorna True se o seed foi aplicado."""
    from core.db import db as db_default

    database = database or db_default
    if not banco_vazio(database):
        return False

    database.init_db()

    # Usuários
    for nome, email, perfil in USUARIOS_SEED:
        database.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (?, ?, ?, ?)",
            (nome, email.lower(), hash_senha(SENHA_DEV), perfil),
        )

    # Empresas parceiras
    database.execute(
        "INSERT INTO empresas_parceiras (razao_social, cnpj, ativo) VALUES (?, ?, 1)",
        ("Transportes Vale Sul Ltda", "12.345.678/0001-90"),
    )
    database.execute(
        "INSERT INTO empresas_parceiras (razao_social, cnpj, ativo) VALUES (?, ?, 1)",
        ("Carretas Minas Gerais ME", "98.765.432/0001-10"),
    )

    # Veículos (1 roll-on, 2 garra)
    database.execute(
        """INSERT INTO veiculos
           (placa, descricao, tipo, capacidade_kg, tempo_execucao_padrao_minutos, terceirizado, ativo)
           VALUES (?, ?, ?, ?, ?, 0, 1)""",
        ("QAL1A01", "Roll-on — troca de caçamba", "roll_on", 12000, 22),
    )
    database.execute(
        """INSERT INTO veiculos
           (placa, descricao, tipo, capacidade_kg, tempo_execucao_padrao_minutos, terceirizado, ativo)
           VALUES (?, ?, ?, ?, ?, 0, 1)""",
        ("QAL1A02", "Garra 1 — pátios", "garra", 15000, 30),
    )
    database.execute(
        """INSERT INTO veiculos
           (placa, descricao, tipo, capacidade_kg, tempo_execucao_padrao_minutos, terceirizado, ativo)
           VALUES (?, ?, ?, ?, ?, 0, 1)""",
        ("QAL1A03", "Garra 2 — pátios", "garra", 15000, 30),
    )

    # Motoristas internos (vinculados aos usuários seed quando possível)
    row_mot = database.query_one("SELECT id FROM usuarios WHERE perfil = 'motorista'")
    mot_usuario_id = row_mot["id"] if row_mot else None
    database.execute(
        """INSERT INTO motoristas (nome, cpf, cnh, telefone, tipo, usuario_id, ativo)
           VALUES (?, ?, ?, ?, 'interno', ?, 1)""",
        ("João Pereira", "111.222.333-44", "MG-123456", "(31) 99999-1001", mot_usuario_id),
    )
    database.execute(
        """INSERT INTO motoristas (nome, cpf, cnh, telefone, tipo, ativo)
           VALUES (?, ?, ?, ?, 'interno', 1)""",
        ("Carlos Souza", "222.333.444-55", "MG-123457", "(31) 99999-1002"),
    )
    database.execute(
        """INSERT INTO motoristas (nome, cpf, cnh, telefone, tipo, ativo)
           VALUES (?, ?, ?, ?, 'interno', 1)""",
        ("Antônio Lima", "333.444.555-66", "MG-123458", "(31) 99999-1003"),
    )

    # Fornecedor + ponto de coleta exemplo
    fid = database.execute(
        "INSERT INTO fornecedores (razao_social, nome_fantasia, telefone, frequente, ativo) VALUES (?, ?, ?, 1, 1)",
        ("Metalúrgica Centro Ltda", "Centro Sucata", "(31) 3222-1010"),
    )
    database.execute(
        """INSERT INTO pontos_coleta
           (fornecedor_id, nome, logradouro, numero, bairro, cidade, uf, cep,
            latitude, longitude, nome_responsavel, contato_responsavel,
            tipo_veiculo_padrao, peso_gatilho_kg, distancia_patio_km,
            tempo_deslocamento_minutos, ativo)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            fid,
            "Pátio Centro",
            "Rua das Indústrias",
            "1200",
            "Centro",
            "Belo Horizonte",
            "MG",
            "30140-000",
            -19.9167,
            -43.9345,
            "Roberto Alves",
            "(31) 99999-2001",
            "garra",
            2000,
            8,
            20,
        ),
    )

    return True


def garantir_seed() -> None:
    from core.db import db as db_default

    try:
        db_default.init_db()
    except Exception:
        pass
    if banco_vazio(db_default):
        executar_seed(db_default)
