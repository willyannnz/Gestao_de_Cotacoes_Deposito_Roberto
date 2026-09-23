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

CREATE TABLE IF NOT EXISTS cotacao_mensal (
    mes_referencia TEXT PRIMARY KEY, -- formato YYYY-MM
    criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Cada mês tem sua própria seleção variável de produtos e quantidades.
CREATE TABLE IF NOT EXISTS cotacao_mensal_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mes_referencia TEXT NOT NULL REFERENCES cotacao_mensal(mes_referencia) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES produto(id),
    quantidade REAL NOT NULL DEFAULT 1 CHECK (quantidade > 0),
    UNIQUE(mes_referencia, produto_id)
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
