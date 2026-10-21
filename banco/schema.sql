-- Classe Usuario
CREATE TABLE usuario (
    id            INTEGER      PRIMARY KEY,              -- identificador único
    nome          VARCHAR(60)  NOT NULL UNIQUE,          -- nome de aventureiro 
    email         VARCHAR(120) NOT NULL UNIQUE,          -- e-mail 
    senha         VARCHAR(128) NOT NULL,                 -- senha em texto puro
    moedas        INTEGER      NOT NULL DEFAULT 100,     -- saldo
    admin         BOOLEAN      DEFAULT 0,                -- 1 = administrador
    banido        BOOLEAN      DEFAULT 0,                -- 1 = conta banida
    ultimo_bonus  DATETIME                               -- último bônus diário resgatado
);

-- Classe Transacao (extrato de moedas)
CREATE TABLE transacao (
    id          INTEGER      PRIMARY KEY,
    usuario_id  INTEGER      NOT NULL,                   
    valor       INTEGER      NOT NULL,                  
    motivo      VARCHAR(120),
    criado_em   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuario (id)
);

-- Classe Mesa
CREATE TABLE mesa (
    id             INTEGER      PRIMARY KEY,
    titulo         VARCHAR(100) NOT NULL,
    sistema        VARCHAR(60),                         
    descricao      TEXT,
    preco          INTEGER      DEFAULT 0,             
    recompensa     INTEGER      DEFAULT 50,           
    max_jogadores  INTEGER      DEFAULT 5,
    concluida      BOOLEAN      DEFAULT 0,
    mestre_id      INTEGER      NOT NULL,            
    FOREIGN KEY (mestre_id) REFERENCES usuario (id)
);

-- Classe Livro
CREATE TABLE livro (
    id         INTEGER      PRIMARY KEY,
    titulo     VARCHAR(100) NOT NULL,
    categoria  VARCHAR(60),
    descricao  TEXT,
    preco      INTEGER      DEFAULT 0,               
    arquivo    VARCHAR(200) NOT NULL
);

-- Ligação N para N: quais usuários estão em quais mesas
CREATE TABLE participantes (
    usuario_id  INTEGER NOT NULL,
    mesa_id     INTEGER NOT NULL,
    PRIMARY KEY (usuario_id, mesa_id),              
    FOREIGN KEY (usuario_id) REFERENCES usuario (id),
    FOREIGN KEY (mesa_id)    REFERENCES mesa (id)
);

-- Ligação N para N: quais usuários compraram quais livros
CREATE TABLE livros_comprados (
    usuario_id  INTEGER NOT NULL,
    livro_id    INTEGER NOT NULL,
    PRIMARY KEY (usuario_id, livro_id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id),
    FOREIGN KEY (livro_id)   REFERENCES livro (id)
);
