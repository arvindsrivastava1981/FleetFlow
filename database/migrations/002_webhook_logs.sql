-- ============================================================================
-- Migration 002 — Webhook deduplication ledger (`webhook_logs`)
--
-- Applies to databases already created from schema.sql BEFORE the webhook_logs
-- table was added. The table is also defined natively in database/schema.sql
-- (now table #8), so this migration is idempotent for fresh installs and only
-- adds the table on existing databases that predate this change.
--
-- Motive: the Razorpay `/billing/webhook` handler applies side effects
-- (activate plan / bump vehicle limit). A retried delivery of the same event
-- could apply them twice. `event_id` UNIQUE makes the second delivery a no-op.
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,     -- Razorpay event.id (stable across retries)
    event_type VARCHAR(64) NOT NULL,          -- e.g. payment_link.paid / subscription.activated
    payload JSONB NOT NULL,                   -- raw event body for audit/replay
    status VARCHAR(20) NOT NULL DEFAULT 'PROCESSED'
        CHECK (status IN ('PROCESSED', 'SKIPPED', 'FAILED')),
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_event_id ON webhook_logs(event_id);