from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

participantes = db.Table(
    "participantes",
    db.Column("usuario_id", db.ForeignKey("usuario.id"), primary_key=True),
    db.Column("mesa_id", db.ForeignKey("mesa.id"), primary_key=True),
)
livros_comprados = db.Table(
    "livros_comprados",
    db.Column("usuario_id", db.ForeignKey("usuario.id"), primary_key=True),
    db.Column("livro_id", db.ForeignKey("livro.id"), primary_key=True),
)


class Transacao(db.Model):
    """Extrato: toda entrada ou saída de moedas fica registrada."""
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.ForeignKey("usuario.id"), nullable=False)
    valor = db.Column(db.Integer, nullable=False)  # positivo = crédito
    motivo = db.Column(db.String(120), default="")
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class Usuario(UserMixin, db.Model):
    BONUS_DIARIO = 20

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(60), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(128), nullable=False)
    moedas = db.Column(db.Integer, default=100, nullable=False)
    admin = db.Column(db.Boolean, default=False)
    banido = db.Column(db.Boolean, default=False)
    ultimo_bonus = db.Column(db.DateTime)
    transacoes = db.relationship("Transacao", backref="usuario",
                                 order_by="Transacao.id.desc()",
                                 cascade="all, delete-orphan")

    def definir_senha(self, senha):
        self.senha = senha

    def checar_senha(self, senha):
        return self.senha == senha

    def pode_pagar(self, valor):
        return self.moedas >= valor

    def creditar(self, valor, motivo=""):
        self.moedas += valor
        if valor > 0:
            self.transacoes.append(Transacao(valor=valor, motivo=motivo))

    def debitar(self, valor, motivo=""):
        if not self.pode_pagar(valor):
            raise ValueError("Moedas insuficientes.")
        self.moedas -= valor
        if valor > 0:
            self.transacoes.append(Transacao(valor=-valor, motivo=motivo))

    def bonus_disponivel(self):
        return (self.ultimo_bonus is None
                or datetime.utcnow() - self.ultimo_bonus >= timedelta(hours=24))

    def resgatar_bonus(self):
        if not self.bonus_disponivel():
            raise ValueError("Bônus diário já resgatado. Volte em 24 horas.")
        self.ultimo_bonus = datetime.utcnow()
        self.creditar(self.BONUS_DIARIO, "Bônus diário")


class Mesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    sistema = db.Column(db.String(60), default="")    # D&D 5e, Tormenta20...
    descricao = db.Column(db.Text, default="")
    preco = db.Column(db.Integer, default=0)
    recompensa = db.Column(db.Integer, default=50)
    max_jogadores = db.Column(db.Integer, default=5)
    concluida = db.Column(db.Boolean, default=False)
    mestre_id = db.Column(db.ForeignKey("usuario.id"), nullable=False)
    mestre = db.relationship("Usuario", foreign_keys=[mestre_id])
    jogadores = db.relationship("Usuario", secondary=participantes, backref="mesas")

    def lotada(self):
        return len(self.jogadores) >= self.max_jogadores

    def entrar(self, usuario):
        if self.concluida:
            raise ValueError("Esta mesa já foi concluída.")
        if usuario in self.jogadores:
            raise ValueError("Você já está nesta mesa.")
        if self.lotada():
            raise ValueError("Mesa lotada.")
        usuario.debitar(self.preco, f"Vaga na mesa: {self.titulo}")
        self.jogadores.append(usuario)

    def concluir(self):
        if self.concluida:
            raise ValueError("Mesa já concluída.")
        for jogador in self.jogadores:
            jogador.creditar(self.recompensa, f"Mesa concluída: {self.titulo}")
        self.concluida = True


class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(60), default="")
    descricao = db.Column(db.Text, default="")
    preco = db.Column(db.Integer, default=0)
    arquivo = db.Column(db.String(200), nullable=False)
    compradores = db.relationship("Usuario", secondary=livros_comprados, backref="livros")

    def liberado_para(self, usuario):
        return self.preco == 0 or usuario.admin or usuario in self.compradores

    def comprar(self, usuario):
        if self.liberado_para(usuario):
            raise ValueError("Você já possui este livro.")
        usuario.debitar(self.preco, f"Livro: {self.titulo}")
        self.compradores.append(usuario)
