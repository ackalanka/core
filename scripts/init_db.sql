-- Initial database setup for CardioVoice
-- This script runs automatically when the PostgreSQL container starts

-- Enable pgvector extension for vector similarity search (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'CardioVoice database initialized with pgvector extension';
END $$;
