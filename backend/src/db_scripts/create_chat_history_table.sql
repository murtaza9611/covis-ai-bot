CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_chat_history_session_id
    ON chat_history (session_id);

CREATE INDEX IF NOT EXISTS ix_chat_history_session_created_at
    ON chat_history (session_id, created_at DESC);
