-- Todas as contas
SELECT id, nome, email, moedas, admin, banido FROM usuario;

-- Mesas com o nome do mestre
SELECT mesa.titulo, mesa.sistema, usuario.nome AS mestre
FROM mesa JOIN usuario ON usuario.id = mesa.mestre_id;

-- Jogadores de cada mesa    
SELECT mesa.titulo, usuario.nome AS jogador
FROM participantes
JOIN mesa    ON mesa.id    = participantes.mesa_id
JOIN usuario ON usuario.id = participantes.usuario_id
ORDER BY mesa.titulo;

-- Extrato de um usuário     
SELECT criado_em, motivo, valor
FROM transacao WHERE usuario_id = 1 ORDER BY id DESC;

-- Estante de livros de um usuário 
SELECT livro.titulo
FROM livros_comprados JOIN livro ON livro.id = livros_comprados.livro_id
WHERE livros_comprados.usuario_id = 1;

-- Livros mais comprados
SELECT livro.titulo, COUNT(*) AS compras
FROM livros_comprados JOIN livro ON livro.id = livros_comprados.livro_id
GROUP BY livro.id ORDER BY compras DESC;

-- Total de moedas em circulação   
SELECT COALESCE(SUM(moedas), 0) FROM usuario;

-- Busca de mesas por texto        
SELECT * FROM mesa WHERE titulo LIKE '%d&d%' OR sistema LIKE '%d&d%';

-- Operações de escrita
INSERT INTO usuario (nome, email, senha) VALUES ('Ana', 'ana@email.com', '123456');  -- registro
UPDATE usuario SET moedas = moedas - 30 WHERE id = 1;                                -- debitar
UPDATE usuario SET banido = 1 WHERE id = 2;                                          -- banir
DELETE FROM mesa WHERE id = 3;                                                       -- remover mesa
