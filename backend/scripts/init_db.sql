-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create application role (less privileges than superuser)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'medagent_app') THEN
        CREATE ROLE medagent_app LOGIN PASSWORD 'medagent_secret';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE medagent_db TO medagent_app;
GRANT USAGE ON SCHEMA public TO medagent_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO medagent_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO medagent_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO medagent_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO medagent_app;
