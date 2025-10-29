import os
import sys
import asyncio
from pathlib import Path
import pytest

# Ensure backend root is importable for tests
BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Force a stable absolute SQLite DB path for tests to avoid CWD issues
DB_DIR = os.path.join(BACKEND_ROOT, "data", "database")
os.makedirs(DB_DIR, exist_ok=True)
ABS_DB_PATH = os.path.join(DB_DIR, "stocks_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{ABS_DB_PATH.replace('\\', '/')}" )

# httpx compatibility shim: allow AsyncClient(app=app, base_url=...)
try:
    import httpx
    from httpx import ASGITransport

    _OrigAsyncClient = httpx.AsyncClient

    class _PatchedAsyncClient(_OrigAsyncClient):
        def __init__(self, *args, app=None, base_url=None, **kwargs):  # type: ignore[no-redef]
            if app is not None and "transport" not in kwargs:
                try:
                    kwargs["transport"] = ASGITransport(app=app, lifespan="on")
                except TypeError:
                    # older/newer httpx signature fallback
                    kwargs["transport"] = ASGITransport(app=app)
            if base_url is not None and "base_url" not in kwargs:
                kwargs["base_url"] = base_url
            super().__init__(*args, **kwargs)

    httpx.AsyncClient = _PatchedAsyncClient  # type: ignore[assignment]
except Exception:
    # If httpx is unavailable or API changes, tests may fail; this is best-effort.
    pass

# Ensure SQLite DB and tables exist before tests (for httpx transport compat)
try:
    # Make sure DB directory exists (already ensured above)

    # Import models so metadata contains all tables
    from app.models import strategy as _models  # noqa: F401
    from app.core.database import init_db

    asyncio.run(init_db())
except Exception:
    # Tests that mock/fallback paths should still pass even if init fails
    pass


# Clean DB before each test to avoid cross-test pollution
@pytest.fixture(autouse=True)
def _clear_db_before_test():
    async def _do_clear():
        try:
            from sqlalchemy import delete
            from app.core.database import AsyncSessionLocal
            from app.models.strategy import Strategy, StrategySignal

            async with AsyncSessionLocal() as session:
                await session.execute(delete(StrategySignal))
                await session.execute(delete(Strategy))
                await session.commit()
        except Exception:
            pass

    try:
        asyncio.run(_do_clear())
    except RuntimeError:
        # If already inside an event loop, schedule and wait
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_do_clear())
