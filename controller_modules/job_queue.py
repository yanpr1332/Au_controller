"""Durable offline production queue with explicit recovery of interrupted work."""
from pathlib import Path
import sqlite3
import json
import time
import uuid
from contextlib import contextmanager


class AuditionJobQueue:
    @staticmethod
    @contextmanager
    def _queue_connect(database):
        path = Path(database).resolve()
        if not path.parent.is_dir():
            raise ValueError('Existing database parent directory required')
        db = sqlite3.connect(path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, state TEXT NOT NULL, spec TEXT NOT NULL, output TEXT NOT NULL, result TEXT, error TEXT, updated REAL NOT NULL)')
        try:
            with db:
                yield db
        finally:
            db.close()

    @classmethod
    def enqueue_production_job(cls, database, spec, output_dir):
        plan = cls.production_job_plan(spec, output_dir)
        ident = uuid.uuid4().hex
        with cls._queue_connect(database) as db:
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)',
                       (ident, 'pending', json.dumps(spec, allow_nan=False), plan['destination'], None, None, time.time()))
        return dict(job_id=ident, state='pending', plan=plan)

    @classmethod
    def production_queue_status(cls, database):
        with cls._queue_connect(database) as db:
            rows = db.execute('SELECT id,state,output,result,error,updated FROM jobs ORDER BY updated,id').fetchall()
        return [dict(row) for row in rows]

    @classmethod
    def run_next_production_job(cls, database, *, confirm=False):
        if type(confirm) is not bool:
            raise ValueError('confirm must be Boolean')
        with cls._queue_connect(database) as db:
            # Claim under a write transaction; workers cannot claim the same job.
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM jobs WHERE state='pending' ORDER BY updated,id LIMIT 1").fetchone()
            if row is None:
                return dict(state='idle')
            if not confirm:
                return dict(dry_run=True, job_id=row['id'], output=row['output'])
            db.execute("UPDATE jobs SET state='running',updated=? WHERE id=?", (time.time(), row['id']))
        try:
            result = cls.run_production_jobs(json.loads(row['spec']), row['output'], confirm=True)
        except Exception as exc:
            with cls._queue_connect(database) as db:
                db.execute("UPDATE jobs SET state='failed',error=?,updated=? WHERE id=?",
                           (str(exc), time.time(), row['id']))
            return dict(job_id=row['id'], state='failed', error=str(exc))
        with cls._queue_connect(database) as db:
            db.execute("UPDATE jobs SET state='complete',result=?,updated=? WHERE id=?",
                       (json.dumps(result, allow_nan=False), time.time(), row['id']))
        return dict(job_id=row['id'], state='complete', result=result)

    @classmethod
    def retry_production_job(cls, database, job_id, *, confirm=False):
        """Retry failed/interrupted work only after validating output collisions.

        Running jobs are not reclaimed automatically: the worker could still be alive.
        """
        if type(confirm) is not bool:
            raise ValueError('confirm must be Boolean')
        with cls._queue_connect(database) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None or row['state'] not in ('failed', 'interrupted'):
                raise ValueError('Only failed or explicitly interrupted jobs may be retried')
            plan = cls.production_job_plan(json.loads(row['spec']), row['output'])
            if confirm:
                db.execute("UPDATE jobs SET state='pending',error=NULL,updated=? WHERE id=?", (time.time(), job_id))
        return dict(job_id=job_id, dry_run=not confirm, plan=plan)

    @classmethod
    def mark_production_job_interrupted(cls, database, job_id, *, confirm=False):
        """Operator must first establish that the previous worker has exited."""
        if type(confirm) is not bool:
            raise ValueError('confirm must be Boolean')
        with cls._queue_connect(database) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None or row['state'] != 'running':
                raise ValueError('Expected running job')
            if confirm:
                db.execute("UPDATE jobs SET state='interrupted',updated=? WHERE id=?", (time.time(), job_id))
        return dict(job_id=job_id, dry_run=not confirm)
