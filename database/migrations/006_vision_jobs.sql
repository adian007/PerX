-- Vision analysis job tracking (mirrors Alembic b100_add_vision_jobs_table)

CREATE TABLE IF NOT EXISTS vision_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task            VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'queued',
    request_payload JSONB NOT NULL DEFAULT '{}',
    result_payload  JSONB,
    error_payload   JSONB,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,
    expires_at      TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_vision_jobs_user_id ON vision_jobs(user_id);
CREATE INDEX IF NOT EXISTS ix_vision_jobs_task ON vision_jobs(task);
CREATE INDEX IF NOT EXISTS ix_vision_jobs_status ON vision_jobs(status);
CREATE INDEX IF NOT EXISTS ix_vision_jobs_created_at ON vision_jobs(created_at);
CREATE INDEX IF NOT EXISTS ix_vision_jobs_expires_at ON vision_jobs(expires_at);
