"""Cadastros: fornecedores, pontos de coleta, veículos, motoristas, usuários, disponibilidades."""
from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from core.auth import hash_senha, requer_permissao, requer_perfis
from core.csrf import csrf_protect, gerar_token
from core.db import get_db
from core.models import PERFIS, TIPOS_MOTORISTA, TIPOS_VEICULO

bp_cadastros = Blueprint("cadastros", __name__, url_prefix="/cadastros")


def _cs() -> str:
    return gerar_token()


# ======================= MENU =======================

@bp_cadastros.route("/")
@requer_permissao("cadastros")
def index():
    return render_template("cadastros/index.html", usuario=g.usuario, csrf=_cs())


# ======================= FORNECEDORES =======================

@bp_cadastros.route("/fornecedores")
@requer_permissao("cadastros")
def fornecedores():
    rows = get_db().query(
        """SELECT f.*,
                  (SELECT COUNT(*) FROM pontos_coleta p WHERE p.fornecedor_id = f.id) AS n_pontos
           FROM fornecedores f ORDER BY f.razao_social"""
    )
    return render_template(
        "cadastros/fornecedores.html", rows=rows, usuario=g.usuario, csrf=_cs()
    )


@bp_cadastros.route("/fornecedores/novo", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def fornecedor_novo():
    if request.method == "POST":
        nome = (request.form.get("razao_social") or "").strip()
        if not nome:
            flash("Razão social é obrigatória.", "danger")
        else:
            get_db().execute(
                """INSERT INTO fornecedores
                   (razao_social, nome_fantasia, cnpj_cpf, telefone, email, frequente, ativo)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (
                    nome,
                    (request.form.get("nome_fantasia") or "").strip() or None,
                    (request.form.get("cnpj_cpf") or "").strip() or None,
                    (request.form.get("telefone") or "").strip() or None,
                    (request.form.get("email") or "").strip() or None,
                    1 if request.form.get("frequente") else 0,
                ),
            )
            flash("Fornecedor cadastrado.", "success")
            return redirect(url_for("cadastros.fornecedores"))
    return render_template(
        "cadastros/fornecedor_form.html", row=None, usuario=g.usuario, csrf=_cs()
    )


@bp_cadastros.route("/fornecedores/<int:fid>/editar", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def fornecedor_editar(fid):
    db = get_db()
    row = db.query_one("SELECT * FROM fornecedores WHERE id = ?", (fid,))
    if not row:
        flash("Fornecedor não encontrado.", "warning")
        return redirect(url_for("cadastros.fornecedores"))
    if request.method == "POST":
        nome = (request.form.get("razao_social") or "").strip()
        if not nome:
            flash("Razão social é obrigatória.", "danger")
        else:
            db.execute(
                """UPDATE fornecedores SET razao_social=?, nome_fantasia=?, cnpj_cpf=?,
                   telefone=?, email=?, frequente=?, ativo=? WHERE id=?""",
                (
                    nome,
                    (request.form.get("nome_fantasia") or "").strip() or None,
                    (request.form.get("cnpj_cpf") or "").strip() or None,
                    (request.form.get("telefone") or "").strip() or None,
                    (request.form.get("email") or "").strip() or None,
                    1 if request.form.get("frequente") else 0,
                    1 if request.form.get("ativo") else 0,
                    fid,
                ),
            )
            flash("Fornecedor atualizado.", "success")
            return redirect(url_for("cadastros.fornecedores"))
    return render_template(
        "cadastros/fornecedor_form.html", row=row, usuario=g.usuario, csrf=_cs()
    )


# ======================= PONTOS DE COLETA =======================

@bp_cadastros.route("/pontos")
@requer_permissao("cadastros")
def pontos():
    rows = get_db().query(
        """SELECT p.*, f.razao_social FROM pontos_coleta p
           JOIN fornecedores f ON f.id = p.fornecedor_id
           ORDER BY p.bairro, p.nome"""
    )
    return render_template(
        "cadastros/pontos.html", rows=rows, usuario=g.usuario, csrf=_cs()
    )


@bp_cadastros.route("/pontos/novo", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def ponto_novo():
    db = get_db()
    fornecedores = db.query(
        "SELECT id, razao_social FROM fornecedores WHERE ativo = 1 ORDER BY razao_social"
    )
    if request.method == "POST":
        obrigatorios = ["fornecedor_id", "nome", "logradouro", "bairro", "cidade", "uf", "nome_responsavel"]
        if any(not (request.form.get(c) or "").strip() for c in obrigatorios):
            flash("Preencha todos os campos obrigatórios.", "danger")
        else:
            lat = request.form.get("latitude") or None
            lng = request.form.get("longitude") or None
            # Mock de geocoding: se vazio, deriva de hash do bairro (determinístico)
            if not lat or not lng:
                lat, lng = _mock_coords(
                    request.form.get("bairro", ""), request.form.get("cidade", "")
                )
            db.execute(
                """INSERT INTO pontos_coleta
                   (fornecedor_id, nome, logradouro, numero, bairro, cidade, uf, cep,
                    latitude, longitude, nome_responsavel, contato_responsavel,
                    tipo_veiculo_padrao, peso_gatilho_kg, distancia_patio_km,
                    tempo_deslocamento_minutos, observacoes, ativo)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (
                    int(request.form["fornecedor_id"]),
                    request.form["nome"].strip(),
                    request.form["logradouro"].strip(),
                    (request.form.get("numero") or "").strip() or None,
                    request.form["bairro"].strip(),
                    request.form["cidade"].strip(),
                    request.form["uf"].strip().upper()[:2],
                    (request.form.get("cep") or "").strip() or None,
                    float(lat),
                    float(lng),
                    request.form["nome_responsavel"].strip(),
                    (request.form.get("contato_responsavel") or "").strip() or None,
                    request.form.get("tipo_veiculo_padrao") or "garra",
                    float(request.form["peso_gatilho_kg"]) if request.form.get("peso_gatilho_kg") else None,
                    int(request.form["distancia_patio_km"]) if request.form.get("distancia_patio_km") else None,
                    int(request.form["tempo_deslocamento_minutos"]) if request.form.get("tempo_deslocamento_minutos") else None,
                    (request.form.get("observacoes") or "").strip() or None,
                ),
            )
            flash("Ponto de coleta cadastrado.", "success")
            return redirect(url_for("cadastros.pontos"))
    return render_template(
        "cadastros/ponto_form.html",
        row=None,
        fornecedores=fornecedores,
        tipos=TIPOS_VEICULO,
        usuario=g.usuario,
        csrf=_cs(),
    )


def _mock_coords(bairro: str, cidade: str) -> tuple[float, float]:
    """Coordenadas mock determinísticas (BH como centro de referência)."""
    base_lat, base_lng = -19.9167, -43.9345
    seed = sum(ord(c) for c in f"{bairro}{cidade}".lower()) % 200
    lat = base_lat + (seed - 100) * 0.002
    lng = base_lng + ((seed * 7) % 200 - 100) * 0.002
    return round(lat, 6), round(lng, 6)


@bp_cadastros.route("/pontos/<int:pid>/editar", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def ponto_editar(pid):
    db = get_db()
    row = db.query_one("SELECT * FROM pontos_coleta WHERE id = ?", (pid,))
    if not row:
        flash("Ponto não encontrado.", "warning")
        return redirect(url_for("cadastros.pontos"))
    fornecedores = db.query(
        "SELECT id, razao_social FROM fornecedores WHERE ativo = 1 ORDER BY razao_social"
    )
    if request.method == "POST":
        obrigatorios = ["nome", "logradouro", "bairro", "cidade", "uf", "nome_responsavel"]
        if any(not (request.form.get(c) or "").strip() for c in obrigatorios):
            flash("Preencha todos os campos obrigatórios.", "danger")
        else:
            db.execute(
                """UPDATE pontos_coleta SET nome=?, logradouro=?, numero=?, bairro=?,
                   cidade=?, uf=?, cep=?, nome_responsavel=?, contato_responsavel=?,
                   tipo_veiculo_padrao=?, peso_gatilho_kg=?, distancia_patio_km=?,
                   tempo_deslocamento_minutos=?, observacoes=?, ativo=? WHERE id=?""",
                (
                    request.form["nome"].strip(),
                    request.form["logradouro"].strip(),
                    (request.form.get("numero") or "").strip() or None,
                    request.form["bairro"].strip(),
                    request.form["cidade"].strip(),
                    request.form["uf"].strip().upper()[:2],
                    (request.form.get("cep") or "").strip() or None,
                    request.form["nome_responsavel"].strip(),
                    (request.form.get("contato_responsavel") or "").strip() or None,
                    request.form.get("tipo_veiculo_padrao") or "garra",
                    float(request.form["peso_gatilho_kg"]) if request.form.get("peso_gatilho_kg") else None,
                    int(request.form["distancia_patio_km"]) if request.form.get("distancia_patio_km") else None,
                    int(request.form["tempo_deslocamento_minutos"]) if request.form.get("tempo_deslocamento_minutos") else None,
                    (request.form.get("observacoes") or "").strip() or None,
                    1 if request.form.get("ativo") else 0,
                    pid,
                ),
            )
            flash("Ponto atualizado.", "success")
            return redirect(url_for("cadastros.pontos"))
    return render_template(
        "cadastros/ponto_form.html",
        row=row,
        fornecedores=fornecedores,
        tipos=TIPOS_VEICULO,
        usuario=g.usuario,
        csrf=_cs(),
    )


# ======================= VEÍCULOS =======================

@bp_cadastros.route("/veiculos")
@requer_permissao("cadastros")
def veiculos():
    rows = get_db().query(
        """SELECT v.*, e.razao_social AS parceira FROM veiculos v
           LEFT JOIN empresas_parceiras e ON e.id = v.empresa_parceira_id
           ORDER BY v.placa"""
    )
    return render_template(
        "cadastros/veiculos.html", rows=rows, usuario=g.usuario, csrf=_cs()
    )


@bp_cadastros.route("/veiculos/novo", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def veiculo_novo():
    if request.method == "POST":
        placa = (request.form.get("placa") or "").strip().upper()
        tipo = request.form.get("tipo") or ""
        if not placa or tipo not in TIPOS_VEICULO:
            flash("Placa e tipo são obrigatórios.", "danger")
        else:
            get_db().execute(
                """INSERT INTO veiculos
                   (placa, descricao, tipo, capacidade_kg, tempo_execucao_padrao_minutos,
                    terceirizado, ativo)
                   VALUES (?,?,?,?,?,?,1)""",
                (
                    placa,
                    (request.form.get("descricao") or "").strip() or None,
                    tipo,
                    float(request.form["capacidade_kg"]) if request.form.get("capacidade_kg") else None,
                    int(request.form.get("tempo_execucao_padrao_minutos") or 30),
                    1 if request.form.get("terceirizado") else 0,
                ),
            )
            flash("Veículo cadastrado.", "success")
            return redirect(url_for("cadastros.veiculos"))
    return render_template(
        "cadastros/veiculo_form.html", row=None, tipos=TIPOS_VEICULO,
        usuario=g.usuario, csrf=_cs(),
    )


@bp_cadastros.route("/veiculos/<int:vid>/editar", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def veiculo_editar(vid):
    db = get_db()
    row = db.query_one("SELECT * FROM veiculos WHERE id = ?", (vid,))
    if not row:
        flash("Veículo não encontrado.", "warning")
        return redirect(url_for("cadastros.veiculos"))
    if request.method == "POST":
        placa = (request.form.get("placa") or "").strip().upper()
        tipo = request.form.get("tipo") or ""
        if not placa or tipo not in TIPOS_VEICULO:
            flash("Placa e tipo são obrigatórios.", "danger")
        else:
            db.execute(
                """UPDATE veiculos SET placa=?, descricao=?, tipo=?, capacidade_kg=?,
                   tempo_execucao_padrao_minutos=?, terceirizado=?, ativo=? WHERE id=?""",
                (
                    placa,
                    (request.form.get("descricao") or "").strip() or None,
                    tipo,
                    float(request.form["capacidade_kg"]) if request.form.get("capacidade_kg") else None,
                    int(request.form.get("tempo_execucao_padrao_minutos") or 30),
                    1 if request.form.get("terceirizado") else 0,
                    1 if request.form.get("ativo") else 0,
                    vid,
                ),
            )
            flash("Veículo atualizado.", "success")
            return redirect(url_for("cadastros.veiculos"))
    return render_template(
        "cadastros/veiculo_form.html", row=row, tipos=TIPOS_VEICULO,
        usuario=g.usuario, csrf=_cs(),
    )


# ======================= MOTORISTAS =======================

@bp_cadastros.route("/motoristas")
@requer_permissao("cadastros")
def motoristas():
    rows = get_db().query(
        """SELECT m.*, e.razao_social AS parceira, u.nome AS usuario_nome
           FROM motoristas m
           LEFT JOIN empresas_parceiras e ON e.id = m.empresa_parceira_id
           LEFT JOIN usuarios u ON u.id = m.usuario_id
           ORDER BY m.nome"""
    )
    return render_template(
        "cadastros/motoristas.html", rows=rows, usuario=g.usuario, csrf=_cs()
    )


@bp_cadastros.route("/motoristas/novo", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def motorista_novo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        tipo = request.form.get("tipo") or "interno"
        if not nome or tipo not in TIPOS_MOTORISTA:
            flash("Nome e tipo são obrigatórios.", "danger")
        else:
            get_db().execute(
                """INSERT INTO motoristas
                   (nome, cpf, cnh, telefone, email, tipo, ativo)
                   VALUES (?,?,?,?,?,?,1)""",
                (
                    nome,
                    (request.form.get("cpf") or "").strip() or None,
                    (request.form.get("cnh") or "").strip() or None,
                    (request.form.get("telefone") or "").strip() or None,
                    (request.form.get("email") or "").strip() or None,
                    tipo,
                ),
            )
            flash("Motorista cadastrado.", "success")
            return redirect(url_for("cadastros.motoristas"))
    return render_template(
        "cadastros/motorista_form.html", row=None, tipos=TIPOS_MOTORISTA,
        usuario=g.usuario, csrf=_cs(),
    )


@bp_cadastros.route("/motoristas/<int:mid>/editar", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def motorista_editar(mid):
    db = get_db()
    row = db.query_one("SELECT * FROM motoristas WHERE id = ?", (mid,))
    if not row:
        flash("Motorista não encontrado.", "warning")
        return redirect(url_for("cadastros.motoristas"))
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        tipo = request.form.get("tipo") or "interno"
        if not nome or tipo not in TIPOS_MOTORISTA:
            flash("Nome e tipo são obrigatórios.", "danger")
        else:
            db.execute(
                """UPDATE motoristas SET nome=?, cpf=?, cnh=?, telefone=?, email=?,
                   tipo=?, ativo=? WHERE id=?""",
                (
                    nome,
                    (request.form.get("cpf") or "").strip() or None,
                    (request.form.get("cnh") or "").strip() or None,
                    (request.form.get("telefone") or "").strip() or None,
                    (request.form.get("email") or "").strip() or None,
                    tipo,
                    1 if request.form.get("ativo") else 0,
                    mid,
                ),
            )
            flash("Motorista atualizado.", "success")
            return redirect(url_for("cadastros.motoristas"))
    return render_template(
        "cadastros/motorista_form.html", row=row, tipos=TIPOS_MOTORISTA,
        usuario=g.usuario, csrf=_cs(),
    )


# ======================= DISPONIBILIDADES =======================

@bp_cadastros.route("/disponibilidades", methods=["GET", "POST"])
@requer_permissao("cadastros")
@csrf_protect
def disponibilidades():
    db = get_db()
    if request.method == "POST":
        mid = request.form.get("motorista_id")
        inicio = request.form.get("inicio")
        fim = request.form.get("fim")
        if not mid or not inicio or not fim:
            flash("Preencha motorista, início e fim.", "danger")
        else:
            db.execute(
                """INSERT INTO disponibilidades_motorista
                   (motorista_id, inicio, fim, disponivel, motivo)
                   VALUES (?,?,?,?,?)""",
                (
                    int(mid),
                    inicio,
                    fim,
                    1 if request.form.get("disponivel", "1") == "1" else 0,
                    (request.form.get("motivo") or "").strip() or None,
                ),
            )
            flash("Disponibilidade registrada.", "success")
            return redirect(url_for("cadastros.disponibilidades"))
    rows = db.query(
        """SELECT d.*, m.nome AS motorista_nome
           FROM disponibilidades_motorista d
           JOIN motoristas m ON m.id = d.motorista_id
           ORDER BY d.inicio DESC LIMIT 50"""
    )
    motoristas = db.query(
        "SELECT id, nome FROM motoristas WHERE ativo = 1 ORDER BY nome"
    )
    return render_template(
        "cadastros/disponibilidades.html",
        rows=rows,
        motoristas=motoristas,
        usuario=g.usuario,
        csrf=_cs(),
    )


# ======================= USUÁRIOS (admin) =======================

@bp_cadastros.route("/usuarios")
@requer_perfis("administradora")
def usuarios():
    rows = get_db().query("SELECT id, nome, email, perfil, ativo, criado_em FROM usuarios ORDER BY nome")
    return render_template(
        "cadastros/usuarios.html", rows=rows, perfis=PERFIS,
        usuario=g.usuario, csrf=_cs(),
    )


@bp_cadastros.route("/usuarios/novo", methods=["GET", "POST"])
@requer_perfis("administradora")
@csrf_protect
def usuario_novo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""
        perfil = request.form.get("perfil") or ""
        if not nome or not email or len(senha) < 6 or perfil not in PERFIS:
            flash("Preencha nome, e-mail, senha (≥6) e perfil válido.", "danger")
        elif get_db().query_one("SELECT id FROM usuarios WHERE email = ?", (email,)):
            flash("E-mail já cadastrado.", "danger")
        else:
            get_db().execute(
                "INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (?,?,?,?)",
                (nome, email, hash_senha(senha), perfil),
            )
            flash("Usuário criado.", "success")
            return redirect(url_for("cadastros.usuarios"))
    return render_template(
        "cadastros/usuario_form.html", perfis=PERFIS, usuario=g.usuario, csrf=_cs()
    )
