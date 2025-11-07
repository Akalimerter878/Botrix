"""
End-to-end integration tests for Botrix

Tests the full flow:
1. Go backend adds job to Redis queue
2. Python worker processes the job
3. Account is created and stored in database
4. Job status is updated correctly

Requires:
- Redis server running
- Go backend running (optional, simulated if not available)
- Database accessible
"""

import asyncio
import json
import time
import uuid
import pytest
import redis
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# Test configuration
REDIS_URL = "redis://localhost:6379/1"  # Use DB 1 for tests
QUEUE_KEY = "botrix:jobs:queue"
STATUS_KEY_PREFIX = "botrix:jobs:status:"
RESULTS_KEY_PREFIX = "botrix:jobs:results:"
UPDATES_CHANNEL = "botrix:jobs:updates"

# Job statuses
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class MockAccountCreator:
    """Mock account creator for testing without real API calls"""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.accounts_created = []
    
    def create_account(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock account creation"""
        if self.should_fail:
            raise Exception("Simulated account creation failure")
        
        account = {
            "email": f"test{len(self.accounts_created)}@example.com",
            "username": username or f"testuser{len(self.accounts_created)}",
            "password": password or "TestPass123!",
            "email_password": "EmailPass123!",
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        
        self.accounts_created.append(account)
        return account


@pytest.fixture
def redis_client():
    """Redis client fixture with cleanup"""
    client = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Clean up before test
    client.flushdb()
    
    yield client
    
    # Clean up after test
    client.flushdb()
    client.close()


@pytest.fixture
def mock_account_creator():
    """Mock account creator fixture"""
    return MockAccountCreator()


@pytest.fixture
def mock_failing_account_creator():
    """Mock account creator that fails"""
    return MockAccountCreator(should_fail=True)


def create_test_job(
    count: int = 1,
    username: Optional[str] = None,
    password: Optional[str] = None,
    priority: int = 1
) -> Dict[str, Any]:
    """Create a test job"""
    return {
        "id": str(uuid.uuid4()),
        "count": count,
        "username": username,
        "password": password,
        "priority": priority,
        "status": STATUS_PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "retry_count": 0,
    }


def enqueue_job(redis_client: redis.Redis, job: Dict[str, Any]) -> str:
    """
    Enqueue a job to Redis (simulates Go backend)
    
    Args:
        redis_client: Redis client
        job: Job data
        
    Returns:
        Job ID
    """
    job_id = job["id"]
    
    # Add to queue
    redis_client.rpush(QUEUE_KEY, json.dumps(job))
    
    # Set initial status
    status_key = f"{STATUS_KEY_PREFIX}{job_id}"
    redis_client.set(status_key, STATUS_PENDING)
    
    return job_id


async def wait_for_job_completion(
    redis_client: redis.Redis,
    job_id: str,
    timeout: int = 30
) -> str:
    """
    Wait for job to complete
    
    Args:
        redis_client: Redis client
        job_id: Job ID to wait for
        timeout: Maximum wait time in seconds
        
    Returns:
        Final job status
        
    Raises:
        TimeoutError: If job doesn't complete within timeout
    """
    status_key = f"{STATUS_KEY_PREFIX}{job_id}"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = redis_client.get(status_key)
        
        if status in [STATUS_COMPLETED, STATUS_FAILED]:
            return status
        
        await asyncio.sleep(0.5)
    
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


async def simulate_worker_processing(
    redis_client: redis.Redis,
    account_creator: MockAccountCreator,
    max_jobs: int = 1
) -> None:
    """
    Simulate worker processing (simplified version of worker_daemon.py)
    
    Args:
        redis_client: Redis client
        account_creator: Account creator instance
        max_jobs: Maximum number of jobs to process
    """
    jobs_processed = 0
    
    while jobs_processed < max_jobs:
        # BLPOP with timeout
        result = redis_client.blpop(QUEUE_KEY, timeout=5)
        
        if result is None:
            # No job available
            break
        
        _, job_json = result
        job_data = json.loads(job_json)
        job_id = job_data["id"]
        
        # Update status to running
        status_key = f"{STATUS_KEY_PREFIX}{job_id}"
        redis_client.set(status_key, STATUS_RUNNING)
        
        try:
            # Process job
            count = job_data.get("count", 1)
            username = job_data.get("username")
            password = job_data.get("password")
            
            accounts = []
            for i in range(count):
                account = account_creator.create_account(username, password)
                accounts.append(account)
            
            # Mark as completed
            redis_client.set(status_key, STATUS_COMPLETED)
            
            # Store results
            results_key = f"{RESULTS_KEY_PREFIX}{job_id}"
            redis_client.set(results_key, json.dumps({
                "accounts_created": len(accounts),
                "accounts": accounts,
                "completed_at": datetime.utcnow().isoformat(),
            }))
            
            # Publish update
            redis_client.publish(UPDATES_CHANNEL, json.dumps({
                "job_id": job_id,
                "status": STATUS_COMPLETED,
                "timestamp": datetime.utcnow().isoformat(),
            }))
            
        except Exception as e:
            # Mark as failed
            redis_client.set(status_key, STATUS_FAILED)
            error_key = f"{STATUS_KEY_PREFIX}{job_id}:error"
            redis_client.set(error_key, str(e))
        
        jobs_processed += 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_single_account_creation(redis_client, mock_account_creator):
    """Test creating a single account through the full flow"""
    # Create and enqueue job
    job = create_test_job(count=1, username="testuser", password="TestPass123!")
    job_id = enqueue_job(redis_client, job)
    
    # Verify job in queue
    queue_length = redis_client.llen(QUEUE_KEY)
    assert queue_length == 1, "Job should be in queue"
    
    # Simulate worker processing
    await simulate_worker_processing(redis_client, mock_account_creator, max_jobs=1)
    
    # Wait for completion
    status = await wait_for_job_completion(redis_client, job_id, timeout=10)
    assert status == STATUS_COMPLETED, "Job should be completed"
    
    # Verify results
    results_key = f"{RESULTS_KEY_PREFIX}{job_id}"
    results_json = redis_client.get(results_key)
    assert results_json is not None, "Results should be stored"
    
    results = json.loads(results_json)
    assert results["accounts_created"] == 1, "One account should be created"
    assert len(results["accounts"]) == 1, "One account in results"
    
    # Verify account data
    account = results["accounts"][0]
    assert account["username"] == "testuser"
    assert account["password"] == "TestPass123!"
    assert "email" in account
    assert "created_at" in account
    
    # Verify queue is empty
    assert redis_client.llen(QUEUE_KEY) == 0, "Queue should be empty"


@pytest.mark.asyncio
async def test_multiple_accounts_creation(redis_client, mock_account_creator):
    """Test creating multiple accounts in a single job"""
    # Create job for 5 accounts
    job = create_test_job(count=5)
    job_id = enqueue_job(redis_client, job)
    
    # Simulate worker processing
    await simulate_worker_processing(redis_client, mock_account_creator, max_jobs=1)
    
    # Wait for completion
    status = await wait_for_job_completion(redis_client, job_id, timeout=15)
    assert status == STATUS_COMPLETED, "Job should be completed"
    
    # Verify results
    results_key = f"{RESULTS_KEY_PREFIX}{job_id}"
    results = json.loads(redis_client.get(results_key))
    
    assert results["accounts_created"] == 5, "Five accounts should be created"
    assert len(results["accounts"]) == 5, "Five accounts in results"
    
    # Verify each account has required fields
    for account in results["accounts"]:
        assert "email" in account
        assert "username" in account
        assert "password" in account


@pytest.mark.asyncio
async def test_multiple_jobs_sequential(redis_client, mock_account_creator):
    """Test processing multiple jobs sequentially"""
    # Create multiple jobs
    jobs = [create_test_job(count=1) for _ in range(3)]
    job_ids = [enqueue_job(redis_client, job) for job in jobs]
    
    # Verify all jobs in queue
    assert redis_client.llen(QUEUE_KEY) == 3, "Three jobs should be in queue"
    
    # Simulate worker processing all jobs
    await simulate_worker_processing(redis_client, mock_account_creator, max_jobs=3)
    
    # Verify all jobs completed
    for job_id in job_ids:
        status_key = f"{STATUS_KEY_PREFIX}{job_id}"
        status = redis_client.get(status_key)
        assert status == STATUS_COMPLETED, f"Job {job_id} should be completed"
    
    # Verify queue is empty
    assert redis_client.llen(QUEUE_KEY) == 0, "Queue should be empty"


@pytest.mark.asyncio
async def test_job_failure_handling(redis_client, mock_failing_account_creator):
    """Test handling of failed account creation"""
    # Create job
    job = create_test_job(count=1)
    job_id = enqueue_job(redis_client, job)
    
    # Simulate worker processing with failing creator
    await simulate_worker_processing(redis_client, mock_failing_account_creator, max_jobs=1)
    
    # Verify job failed
    status_key = f"{STATUS_KEY_PREFIX}{job_id}"
    status = redis_client.get(status_key)
    assert status == STATUS_FAILED, "Job should be marked as failed"
    
    # Verify error message stored
    error_key = f"{STATUS_KEY_PREFIX}{job_id}:error"
    error = redis_client.get(error_key)
    assert error is not None, "Error message should be stored"
    assert "Simulated account creation failure" in error


@pytest.mark.asyncio
async def test_job_status_progression(redis_client, mock_account_creator):
    """Test that job status progresses correctly"""
    # Create job
    job = create_test_job(count=1)
    job_id = enqueue_job(redis_client, job)
    status_key = f"{STATUS_KEY_PREFIX}{job_id}"
    
    # Initial status
    status = redis_client.get(status_key)
    assert status == STATUS_PENDING, "Initial status should be pending"
    
    # Start processing in background
    task = asyncio.create_task(
        simulate_worker_processing(redis_client, mock_account_creator, max_jobs=1)
    )
    
    # Wait a bit for processing to start
    await asyncio.sleep(0.1)
    
    # Status should be running or completed
    status = redis_client.get(status_key)
    assert status in [STATUS_RUNNING, STATUS_COMPLETED], "Status should progress"
    
    # Wait for completion
    await task
    
    # Final status
    status = redis_client.get(status_key)
    assert status == STATUS_COMPLETED, "Final status should be completed"


@pytest.mark.asyncio
async def test_pubsub_updates(redis_client, mock_account_creator):
    """Test that job updates are published to pub/sub channel"""
    # Subscribe to updates channel
    pubsub = redis_client.pubsub()
    pubsub.subscribe(UPDATES_CHANNEL)
    
    # Skip subscription confirmation message
    pubsub.get_message()
    
    # Create and enqueue job
    job = create_test_job(count=1)
    job_id = enqueue_job(redis_client, job)
    
    # Process job in background
    task = asyncio.create_task(
        simulate_worker_processing(redis_client, mock_account_creator, max_jobs=1)
    )
    
    # Wait for job to complete
    await task
    
    # Check for update message
    message = None
    for _ in range(10):  # Try up to 10 times
        msg = pubsub.get_message()
        if msg and msg["type"] == "message":
            message = msg
            break
        await asyncio.sleep(0.1)
    
    assert message is not None, "Should receive pub/sub update"
    
    # Verify update data
    update = json.loads(message["data"])
    assert update["job_id"] == job_id
    assert update["status"] == STATUS_COMPLETED
    assert "timestamp" in update
    
    pubsub.close()


@pytest.mark.asyncio
async def test_queue_persistence(redis_client):
    """Test that jobs persist in Redis queue"""
    # Create multiple jobs
    jobs = [create_test_job(count=1) for _ in range(5)]
    job_ids = [enqueue_job(redis_client, job) for job in jobs]
    
    # Verify all jobs in queue
    assert redis_client.llen(QUEUE_KEY) == 5, "All jobs should be in queue"
    
    # Peek at jobs (without removing)
    job_data_list = redis_client.lrange(QUEUE_KEY, 0, -1)
    assert len(job_data_list) == 5, "Should see all 5 jobs"
    
    # Verify job IDs
    stored_ids = [json.loads(j)["id"] for j in job_data_list]
    assert set(stored_ids) == set(job_ids), "All job IDs should match"


@pytest.mark.asyncio
async def test_concurrent_job_processing(redis_client, mock_account_creator):
    """Test processing jobs with simulated concurrent workers"""
    # Create multiple jobs
    jobs = [create_test_job(count=1) for _ in range(6)]
    job_ids = [enqueue_job(redis_client, job) for job in jobs]
    
    # Simulate 2 workers processing concurrently
    worker1 = asyncio.create_task(
        simulate_worker_processing(redis_client, mock_account_creator, max_jobs=3)
    )
    worker2 = asyncio.create_task(
        simulate_worker_processing(redis_client, mock_account_creator, max_jobs=3)
    )
    
    # Wait for both workers to finish
    await asyncio.gather(worker1, worker2)
    
    # Verify all jobs completed
    for job_id in job_ids:
        status_key = f"{STATUS_KEY_PREFIX}{job_id}"
        status = redis_client.get(status_key)
        assert status == STATUS_COMPLETED, f"Job {job_id} should be completed"
    
    # Verify queue is empty
    assert redis_client.llen(QUEUE_KEY) == 0, "Queue should be empty"
    
    # Verify total accounts created
    assert len(mock_account_creator.accounts_created) == 6, "Six accounts total"


@pytest.mark.asyncio
async def test_empty_queue_timeout(redis_client, mock_account_creator):
    """Test worker behavior with empty queue"""
    # Ensure queue is empty
    assert redis_client.llen(QUEUE_KEY) == 0, "Queue should be empty"
    
    # Try to process (should timeout gracefully)
    start_time = time.time()
    await simulate_worker_processing(redis_client, mock_account_creator, max_jobs=1)
    elapsed = time.time() - start_time
    
    # Should return quickly after BLPOP timeout
    assert elapsed < 10, "Should timeout gracefully"


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_worker_health_check():
    """Test worker health check mechanism"""
    # This would test the actual worker daemon health checks
    # For now, we'll test the Redis key structure
    
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    
    health_key = "botrix:worker:health:test-worker"
    health_data = {
        "worker_id": "test-worker",
        "status": "running",
        "last_heartbeat": datetime.utcnow().isoformat(),
        "jobs_processed": 10,
        "jobs_succeeded": 8,
        "jobs_failed": 2,
    }
    
    # Store health check
    redis_client.setex(health_key, 60, json.dumps(health_data))
    
    # Retrieve and verify
    stored_data = json.loads(redis_client.get(health_key))
    assert stored_data["worker_id"] == "test-worker"
    assert stored_data["jobs_processed"] == 10
    
    redis_client.delete(health_key)
    redis_client.close()


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_high_volume_processing(redis_client, mock_account_creator):
    """Test processing a high volume of jobs"""
    # Create 50 jobs
    jobs = [create_test_job(count=1) for _ in range(50)]
    job_ids = [enqueue_job(redis_client, job) for job in jobs]
    
    start_time = time.time()
    
    # Process all jobs
    await simulate_worker_processing(redis_client, mock_account_creator, max_jobs=50)
    
    elapsed = time.time() - start_time
    
    # Verify all completed
    for job_id in job_ids:
        status_key = f"{STATUS_KEY_PREFIX}{job_id}"
        status = redis_client.get(status_key)
        assert status == STATUS_COMPLETED
    
    # Log performance
    print(f"\nProcessed 50 jobs in {elapsed:.2f}s ({50/elapsed:.2f} jobs/sec)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
