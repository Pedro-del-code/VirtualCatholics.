"""
Fé & Caminho — backend em Python (Flask + SQLAlchemy)
Passo 3: troca o SQLite por um banco que persiste de verdade (Postgres no Render),
mantendo SQLite como opção só para rodar na sua máquina.
"""

import os
import re
import secrets
import datetime

import requests
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# O Render fornece DATABASE_URL apontando para o Postgres.
# Sem essa variável (ex: rodando na sua máquina), cai para um SQLite local.
url_banco = os.environ.get("DATABASE_URL", "sqlite:///banco.db")
if url_banco.startswith("postgres://"):
    # SQLAlchemy recente exige o prefixo "postgresql://"
    url_banco = url_banco.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = url_banco
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- modelos ----------

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)


class TokenRecuperacao(db.Model):
    __tablename__ = "tokens_recuperacao"

    token = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False, nullable=False)


with app.app_context():
    db.create_all()


def enviar_email_recuperacao(email_destino, link):
    """Envia o link de redefinição de senha por e-mail via Resend.
    Sem RESEND_API_KEY configurada (ex: rodando localmente), só mostra o link no console."""
    chave_api = os.environ.get("RESEND_API_KEY")
    remetente = os.environ.get("EMAIL_REMETENTE", "onboarding@resend.dev")

    if not chave_api:
        print(f"[DEV] RESEND_API_KEY não configurada. Link de recuperação para {email_destino}: {link}")
        return

    try:
        resposta = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {chave_api}",
                "Content-Type": "application/json",
            },
            json={
                "from": remetente,
                "to": [email_destino],
                "subject": "Recupere o acesso à sua conta — Fé & Caminho",
                "html": (
                    "<p>Olá,</p>"
                    "<p>Recebemos um pedido para redefinir a senha da sua conta em Fé &amp; Caminho.</p>"
                    f'<p><a href="{link}">Clique aqui para criar uma nova senha</a></p>'
                    "<p>Esse link expira em 1 hora. Se você não pediu essa alteração, "
                    "pode ignorar este e-mail com segurança.</p>"
                ),
            },
            timeout=10,
        )
        if resposta.status_code >= 400:
            print(f"[ERRO] Falha ao enviar e-mail via Resend ({resposta.status_code}): {resposta.text}")
    except requests.RequestException as erro:
        print(f"[ERRO] Não foi possível enviar o e-mail de recuperação: {erro}")


# ---------- páginas ----------

@app.route("/")
def tela_login():
    return render_template("entrar.html")


@app.route("/criar-conta")
def tela_criar_conta():
    return render_template("criar-conta.html")


@app.route("/recuperar-senha")
def tela_recuperar_senha():
    return render_template("recuperar-senha.html")


@app.route("/redefinir-senha")
def tela_redefinir_senha():
    token = request.args.get("token", "").strip()
    return render_template("redefinir-senha.html", token=token)


@app.route("/inicio")
def tela_inicio_provisoria():
    # Placeholder até criarmos a página inicial de verdade (próximo passo)
    if "usuario_id" not in session:
        return render_template("entrar.html")
    return "<h1 style='font-family:sans-serif;padding:40px;'>Login funcionando! A página inicial entra no próximo passo.</h1>"


# ---------- api ----------

@app.route("/api/registrar", methods=["POST"])
def registrar():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        return jsonify(erro="Preencha todos os campos."), 400
    if not REGEX_EMAIL.match(email):
        return jsonify(erro="Informe um e-mail válido."), 400
    if len(senha) < 8:
        return jsonify(erro="A senha precisa ter pelo menos 8 caracteres."), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify(erro="Já existe uma conta com esse e-mail."), 409

    usuario = Usuario(nome=nome, email=email, senha_hash=generate_password_hash(senha))
    db.session.add(usuario)
    db.session.commit()
    return jsonify(mensagem="Conta criada com sucesso."), 201


@app.route("/api/entrar", methods=["POST"])
def entrar():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not email or not senha:
        return jsonify(erro="Preencha e-mail e senha."), 400

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario or not check_password_hash(usuario.senha_hash, senha):
        return jsonify(erro="E-mail ou senha incorretos."), 401

    session["usuario_id"] = usuario.id
    return jsonify(mensagem=f"Bem-vindo, {usuario.nome}."), 200


@app.route("/api/recuperar-senha", methods=["POST"])
def recuperar_senha():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()

    if not REGEX_EMAIL.match(email):
        return jsonify(erro="Informe um e-mail válido."), 400

    usuario = Usuario.query.filter_by(email=email).first()

    # Sempre responde com sucesso, exista ou não a conta,
    # para não revelar quais e-mails estão cadastrados.
    if usuario:
        token = secrets.token_urlsafe(32)
        expira_em = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        db.session.add(TokenRecuperacao(token=token, email=email, expira_em=expira_em))
        db.session.commit()

        url_base = os.environ.get("APP_URL", request.host_url.rstrip("/"))
        link = f"{url_base}/redefinir-senha?token={token}"
        enviar_email_recuperacao(email, link)

    return jsonify(mensagem="Se existir uma conta com esse e-mail, enviamos o link de recuperação."), 200


@app.route("/api/redefinir-senha", methods=["POST"])
def redefinir_senha():
    dados = request.get_json(silent=True) or {}
    token = (dados.get("token") or "").strip()
    senha = dados.get("senha") or ""

    if not token:
        return jsonify(erro="Link inválido ou incompleto."), 400
    if len(senha) < 8:
        return jsonify(erro="A senha precisa ter pelo menos 8 caracteres."), 400

    registro = TokenRecuperacao.query.filter_by(token=token).first()
    if not registro or registro.usado or registro.expira_em < datetime.datetime.utcnow():
        return jsonify(erro="Esse link expirou ou já foi usado. Peça a recuperação novamente."), 400

    usuario = Usuario.query.filter_by(email=registro.email).first()
    if not usuario:
        return jsonify(erro="Conta não encontrada."), 404

    usuario.senha_hash = generate_password_hash(senha)
    registro.usado = True
    db.session.commit()
    return jsonify(mensagem="Senha redefinida com sucesso. Já pode entrar."), 200


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta, debug=True)
