import os
import uuid
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, abort, send_from_directory)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from werkzeug.utils import secure_filename
from models import db, Usuario, Mesa, Livro

ADMIN_USER = os.environ.get("ADMIN_USER", "ADMIN")
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "258741")
PACOTES_MOEDAS = {"pequeno": (100, "R$ 5,00"), "medio": (550, "R$ 25,00"),
                  "grande": (1200, "R$ 50,00")}


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def garantir_admin():
    u = Usuario.query.filter(db.func.lower(Usuario.nome) == ADMIN_USER.lower()).first()
    if not u:
        u = Usuario(nome=ADMIN_USER, email="admin@local", moedas=0)
        db.session.add(u)
    u.admin, u.banido = True, False
    u.definir_senha(ADMIN_SENHA)
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "troque-esta-chave")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rpg.db"
    app.config["UPLOAD_DIR"] = os.path.join(app.instance_path, "livros")
    app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    db.init_app(app)
    login = LoginManager(app)
    login.login_view = "login"
    login.login_message = "Entre na sua conta para continuar."

    @login.user_loader
    def carregar(uid):
        return db.session.get(Usuario, int(uid))

    @app.before_request
    def checar_banido():
        if current_user.is_authenticated and current_user.banido:
            logout_user()
            flash("Sua conta foi banida.")

    # ---------- Conta ----------
    @app.route("/")
    def index():
        return redirect(url_for("mesas"))

    @app.route("/registro", methods=["GET", "POST"])
    def registro():
        if request.method == "POST":
            nome = request.form["nome"].strip()
            email = request.form["email"].strip().lower()
            senha = request.form["senha"]
            if nome.lower() == ADMIN_USER.lower():
                flash("Este nome é reservado.")
            elif len(senha) < 6:
                flash("A senha precisa ter ao menos 6 caracteres.")
            elif Usuario.query.filter((db.func.lower(Usuario.nome) == nome.lower())
                                      | (Usuario.email == email)).first():
                flash("Nome ou e-mail já cadastrado.")
            else:
                u = Usuario(nome=nome, email=email)
                u.definir_senha(senha)
                db.session.add(u)
                db.session.commit()
                login_user(u)
                return redirect(url_for("mesas"))
        return render_template("registro.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            ident = request.form["login"].strip().lower()
            u = Usuario.query.filter((db.func.lower(Usuario.nome) == ident)
                                     | (Usuario.email == ident)).first()
            if u and u.checar_senha(request.form["senha"]):
                if u.banido:
                    flash("Sua conta foi banida.")
                else:
                    login_user(u)
                    return redirect(url_for("painel" if u.admin else "mesas"))
            else:
                flash("Usuário ou senha incorretos.")
        return render_template("login.html")

    @app.route("/sair")
    @login_required
    def sair():
        logout_user()
        return redirect(url_for("mesas"))

    # ---------- Mesas (listagem pública) ----------
    @app.route("/mesas")
    def mesas():
        q = request.args.get("q", "").strip()
        consulta = Mesa.query
        if q:
            consulta = consulta.filter(Mesa.titulo.ilike(f"%{q}%") | Mesa.sistema.ilike(f"%{q}%"))
        return render_template("mesas.html", mesas=consulta.order_by(Mesa.id.desc()).all())

    @app.route("/mesas/nova", methods=["POST"])
    @login_required
    def nova_mesa():
        m = Mesa(titulo=request.form["titulo"].strip(),
                 sistema=request.form.get("sistema", "").strip(),
                 descricao=request.form.get("descricao", ""),
                 preco=max(0, int(request.form.get("preco") or 0)),
                 recompensa=max(0, int(request.form.get("recompensa") or 0)),
                 max_jogadores=max(1, int(request.form.get("max_jogadores") or 5)),
                 mestre=current_user)
        m.jogadores.append(current_user)
        db.session.add(m)
        db.session.commit()
        flash("Mesa criada.")
        return redirect(url_for("painel" if current_user.admin else "mesas"))

    @app.route("/mesas/<int:mesa_id>/entrar", methods=["POST"])
    @login_required
    def entrar_mesa(mesa_id):
        m = db.get_or_404(Mesa, mesa_id)
        try:
            m.entrar(current_user)
            db.session.commit()
            flash(f"Você entrou em “{m.titulo}”.")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("mesas"))

    @app.route("/mesas/<int:mesa_id>/concluir", methods=["POST"])
    @login_required
    def concluir_mesa(mesa_id):
        m = db.get_or_404(Mesa, mesa_id)
        if m.mestre_id != current_user.id and not current_user.admin:
            abort(403)
        try:
            m.concluir()
            db.session.commit()
            flash(f"Mesa concluída: {m.recompensa} moedas para cada jogador.")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("mesas"))

    # ---------- Livros ----------
    @app.route("/livros")
    def livros():
        q = request.args.get("q", "").strip()
        consulta = Livro.query
        if q:
            consulta = consulta.filter(Livro.titulo.ilike(f"%{q}%") | Livro.categoria.ilike(f"%{q}%"))
        return render_template("livros.html", livros=consulta.order_by(Livro.id.desc()).all())

    @app.route("/livros/<int:livro_id>/comprar", methods=["POST"])
    @login_required
    def comprar_livro(livro_id):
        l = db.get_or_404(Livro, livro_id)
        try:
            l.comprar(current_user)
            db.session.commit()
            flash(f"“{l.titulo}” adicionado à sua estante.")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("livros"))

    @app.route("/livros/<int:livro_id>/baixar")
    @login_required
    def baixar_livro(livro_id):
        l = db.get_or_404(Livro, livro_id)
        if not l.liberado_para(current_user):
            abort(403)
        return send_from_directory(app.config["UPLOAD_DIR"], l.arquivo)

    # ---------- Moeda ----------
    @app.route("/moeda")
    @login_required
    def moeda():
        return render_template("moeda.html", pacotes=PACOTES_MOEDAS)

    @app.route("/moeda/comprar/<pacote>", methods=["POST"])
    @login_required
    def comprar_moeda(pacote):
        if pacote not in PACOTES_MOEDAS:
            abort(404)
        # SIMULAÇÃO: troque por Pix/Mercado Pago/Stripe antes de ir a produção.
        current_user.creditar(PACOTES_MOEDAS[pacote][0], f"Pacote de moedas ({pacote})")
        db.session.commit()
        flash("Moedas adicionadas (compra simulada).")
        return redirect(url_for("moeda"))

    # ---------- Painel admin ----------
    @app.route("/admin")
    @admin_required
    def painel():
        return render_template("admin.html", usuarios=Usuario.query.order_by(Usuario.id).all(),
                               mesas=Mesa.query.all(), livros=Livro.query.all(),
                               total_moedas=db.session.query(
                                   db.func.coalesce(db.func.sum(Usuario.moedas), 0)).scalar())

    @app.route("/admin/livros/novo", methods=["POST"])
    @admin_required
    def novo_livro():
        pdf = request.files.get("pdf")
        if not pdf or not pdf.filename.lower().endswith(".pdf"):
            flash("Envie um arquivo PDF.")
            return redirect(url_for("painel"))
        nome = f"{uuid.uuid4().hex}_{secure_filename(pdf.filename)}"
        pdf.save(os.path.join(app.config["UPLOAD_DIR"], nome))
        db.session.add(Livro(titulo=request.form["titulo"].strip(),
                             categoria=request.form.get("categoria", "").strip(),
                             descricao=request.form.get("descricao", ""),
                             preco=max(0, int(request.form.get("preco") or 0)),
                             arquivo=nome))
        db.session.commit()
        flash("Livro publicado. Todos já podem ver.")
        return redirect(url_for("painel"))

    @app.route("/admin/livros/<int:livro_id>/remover", methods=["POST"])
    @admin_required
    def remover_livro(livro_id):
        l = db.get_or_404(Livro, livro_id)
        try:
            os.remove(os.path.join(app.config["UPLOAD_DIR"], l.arquivo))
        except OSError:
            pass
        db.session.delete(l)
        db.session.commit()
        flash("Livro removido.")
        return redirect(url_for("painel"))

    @app.route("/admin/mesas/<int:mesa_id>/remover", methods=["POST"])
    @admin_required
    def remover_mesa(mesa_id):
        db.session.delete(db.get_or_404(Mesa, mesa_id))
        db.session.commit()
        flash("Mesa removida.")
        return redirect(url_for("painel"))

    @app.route("/admin/usuarios/<int:uid>/banir", methods=["POST"])
    @admin_required
    def banir_usuario(uid):
        u = db.get_or_404(Usuario, uid)
        if u.admin:
            abort(403)
        u.banido = not u.banido
        db.session.commit()
        flash(f"{u.nome} {'banido' if u.banido else 'desbanido'}.")
        return redirect(url_for("painel"))

    @app.route("/admin/usuarios/<int:uid>/apagar", methods=["POST"])
    @admin_required
    def apagar_usuario(uid):
        u = db.get_or_404(Usuario, uid)
        if u.admin:
            abort(403)
        for m in Mesa.query.filter_by(mestre_id=u.id).all():
            db.session.delete(m)
        db.session.delete(u)
        db.session.commit()
        flash("Conta apagada.")
        return redirect(url_for("painel"))

    # ---------- Perfil e bônus ----------
    @app.route("/perfil")
    @login_required
    def perfil():
        return render_template("perfil.html", transacoes=current_user.transacoes[:15])

    @app.route("/bonus", methods=["POST"])
    @login_required
    def bonus():
        try:
            current_user.resgatar_bonus()
            db.session.commit()
            flash(f"+{current_user.BONUS_DIARIO} moedas de bônus diário.")
        except ValueError as e:
            flash(str(e))
        return redirect(url_for("perfil"))

    @app.route("/admin/usuarios/<int:uid>/moedas", methods=["POST"])
    @admin_required
    def dar_moedas(uid):
        u = db.get_or_404(Usuario, uid)
        u.creditar(max(0, int(request.form.get("valor") or 0)), "Ajuste do administrador")
        db.session.commit()
        flash(f"Moedas enviadas para {u.nome}.")
        return redirect(url_for("painel"))

    with app.app_context():
        db.create_all()
        garantir_admin()
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
