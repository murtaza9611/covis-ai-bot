CREATE TABLE IF NOT EXISTS chat_session_state (
    session_id VARCHAR(255) PRIMARY KEY,
    pending_task_json TEXT
);
