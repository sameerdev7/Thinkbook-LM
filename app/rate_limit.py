"""
Shared slowapi Limiter instance. Keyed by client IP.

Caveat matching the earlier scaling discussion: slowapi's default backend is
in-memory, so like the job system, per-IP counters don't stay in sync across
multiple worker processes. Fine for the single-worker deployment this backend
currently targets; swap the storage_uri to a Redis URL when you move to
multiple workers and nothing else about this file changes.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
