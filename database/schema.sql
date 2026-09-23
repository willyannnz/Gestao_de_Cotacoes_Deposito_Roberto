-- Schema traduzido do Diagrama de Classes UML (Fornecedor, Produto, Cotacao, ConsolidadoMensal, PedidoCompra)
-- Confere se os campos batem com o diagrama real e ajusta se precisar.

CREATE TABLE IF NOT EXISTS fornecedor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    unidade TEXT  -- ex: "1cx", "2cxs"
);

CREATE TABLE IF NOT EXISTS cotacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produto(id),
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedor(id),
    preco REAL NOT NULL CHECK (preco > 0),
    mes_referencia TEXT NOT NULL,  -- formato "2026-09"
    data_registro TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(produto_id, fornecedor_id, mes_referencia)  -- 1 cotação por fornecedor/produto/mês
);

CREATE TABLE IF NOT EXISTS consolidado_mensal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mes_referencia TEXT NOT NULL UNIQUE,
    gerado_em TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedido_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consolidado_id INTEGER NOT NULL REFERENCES consolidado_mensal(id),
    cotacao_vencedora_id INTEGER NOT NULL REFERENCES cotacao(id),  -- RN01 aplicada aqui
    fechado_em TEXT DEFAULT CURRENT_TIMESTAMP
);

-- lista de produtos que precisam ser cotados em cada mês (base pra futura UC06 — pendências)
CREATE TABLE IF NOT EXISTS lista_mes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produto(id),
    mes_referencia TEXT NOT NULL,
    UNIQUE(produto_id, mes_referencia)
);
