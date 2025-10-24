-- PostgreSQL Database Initialization for Homelab Agents
-- Run this script as postgres user after pgvector is installed

-- Enable pgvector extension in template1
\c template1
CREATE EXTENSION IF NOT EXISTS vector;

-- Create databases
CREATE DATABASE agent_memory;
CREATE DATABASE agent_checkpoints;
CREATE DATABASE n8n;

-- Create users (passwords will be set from environment variables)
-- Note: Replace these with actual passwords from .env file
CREATE USER mem0_user WITH PASSWORD 'CHANGE_ME_SecurePassword123!';
CREATE USER agent_user WITH PASSWORD 'CHANGE_ME_SecurePassword456!';
CREATE USER n8n_user WITH PASSWORD 'CHANGE_ME_SecurePassword789!';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agent_memory TO mem0_user;
GRANT ALL PRIVILEGES ON DATABASE agent_checkpoints TO agent_user;
GRANT ALL PRIVILEGES ON DATABASE n8n TO n8n_user;

-- Enable pgvector extension in agent_memory database
\c agent_memory
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO mem0_user;

-- Create Mem0 tables
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    memory TEXT NOT NULL,
    embedding vector(1536),  -- Anthropic embeddings are 1536 dimensions
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);

-- Enable pgvector extension in agent_checkpoints database
\c agent_checkpoints
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO agent_user;

-- LangGraph checkpoint tables (these will be auto-created by LangGraph, but we can prepare)
-- The actual schema is managed by langgraph-checkpoint-postgres package

-- Grant n8n user permissions
\c n8n
GRANT ALL ON SCHEMA public TO n8n_user;

-- Display summary
\c postgres
SELECT 'Database setup complete!' as status;
SELECT datname, pg_encoding_to_char(encoding) as encoding
FROM pg_database
WHERE datname IN ('agent_memory', 'agent_checkpoints', 'n8n');
