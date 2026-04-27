-- migrations/002_jobs_status_check.sql
-- Constrains status to the known set. Defense in depth: the Python
-- JobStatus enum prevents typos in library code, but a stray UPDATE
-- via psql could still corrupt a row without this constraint.
--
-- Wrapped in a DO block because ALTER TABLE ADD CONSTRAINT does not
-- support IF NOT EXISTS, and the test fixture re-applies migrations
-- on every session.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'jobs_status_valid'
    ) THEN
        ALTER TABLE jobs ADD CONSTRAINT jobs_status_valid
            CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'dead_letter'));
    END IF;
END $$;
