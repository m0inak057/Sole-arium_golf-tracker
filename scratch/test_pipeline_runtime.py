import asyncio
import shutil
import traceback
from pathlib import Path
from backend.core.session import create_session
from backend.core.storage import LocalStorage
from backend.orchestrator.pipeline import run_pipeline

async def test_pipeline():
    try:
        storage = LocalStorage()
        session = create_session(gender='male')
        storage.save_session(session)
        d = storage.session_dir(session.session_id)
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy('samples/FO_Demo.mp4', d / 'input.mp4')
        session = await run_pipeline(session, storage)
        print("Final Status Reason:", session.status_reason)
    except Exception as e:
        traceback.print_exc()

asyncio.run(test_pipeline())
