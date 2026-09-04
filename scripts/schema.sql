CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documentos (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, titulo)
);

CREATE INDEX IF NOT EXISTS idx_documentos_tenant_id ON documentos (tenant_id);
CREATE INDEX IF NOT EXISTS idx_documentos_embedding ON documentos
    USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS pedidos (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    numero_pedido TEXT NOT NULL,
    status TEXT NOT NULL,
    previsao_entrega DATE,
    cliente_nome TEXT NOT NULL,
    UNIQUE (tenant_id, numero_pedido)
);

CREATE INDEX IF NOT EXISTS idx_pedidos_tenant_numero ON pedidos (tenant_id, numero_pedido);
