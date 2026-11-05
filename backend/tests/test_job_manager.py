"""
Unit tests for JobManager service.
Verifies concurrency semaphore bounds and detached execution lifecycle.
"""

import asyncio
import pytest
from backend.app.schemas import ConversionOptions, JobStatus, PipelineType
from backend.app.services.job_manager import JobManager


def test_job_manager_concurrency_throttle():
    """Verify JobManager throttles concurrency using asyncio.Semaphore."""
    async def _run_test():
        mgr = JobManager(max_concurrent_jobs=2)
        active_concurrent_peaks = []
        current_running = 0

        async def mock_conversion(entry):
            nonlocal current_running
            current_running += 1
            active_concurrent_peaks.append(current_running)
            await asyncio.sleep(0.1)
            current_running -= 1
            await mgr.emit_complete(entry, "# Result", None)

        mgr._execute_conversion_pipeline = mock_conversion

        # Launch 5 jobs concurrently
        jobs = []
        for _ in range(5):
            j = await mgr.create_job(PipelineType.TEXT_NORMALIZE)
            mgr.submit_job(j.job_id)
            jobs.append(j)

        # Wait for all jobs to complete
        for j in jobs:
            while True:
                detail = await mgr.get_job(j.job_id)
                if detail.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    break
                await asyncio.sleep(0.02)

        # Max peak concurrency should never exceed 2
        assert max(active_concurrent_peaks) <= 2
        statuses = [(await mgr.get_job(j.job_id)).status for j in jobs]
        assert all(s == JobStatus.COMPLETED for s in statuses)

    asyncio.run(_run_test())


def test_job_manager_detached_execution():
    """Verify job continues executing detached after client disconnects."""
    async def _run_test():
        mgr = JobManager()

        job = await mgr.create_job(
            PipelineType.TEXT_NORMALIZE,
            raw_text="<h1>Detached</h1><p>Running in background.</p>",
        )
        mgr.submit_job(job.job_id)

        # Subscribe then immediately mark disconnected
        q = await mgr.subscribe(job.job_id)
        await mgr.unsubscribe(job.job_id, q)
        await mgr.mark_disconnected(job.job_id)

        # Poll until job completes in the background
        for _ in range(50):
            detail = await mgr.get_job(job.job_id)
            if detail.status == JobStatus.COMPLETED:
                break
            await asyncio.sleep(0.05)

        detail = await mgr.get_job(job.job_id)
        assert detail.status == JobStatus.COMPLETED
        assert detail.result is not None
        assert "# Detached" in detail.result.markdown

    asyncio.run(_run_test())


def test_job_manager_cancellation():
    """Verify cancel_job sets cancel_event and transitions to CANCELLED."""
    async def _run_test():
        mgr = JobManager()
        job = await mgr.create_job(PipelineType.TEXT_NORMALIZE)
        await mgr.cancel_job(job.job_id, reason="User cancelled")

        detail = await mgr.get_job(job.job_id)
        assert detail.status == JobStatus.CANCELLED
        assert detail.error.code == "CLIENT_CANCELLED"

    asyncio.run(_run_test())
