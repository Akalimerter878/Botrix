#!/usr/bin/env python3
"""
Botrix Worker Daemon

Consumes jobs from Redis queue and processes account creation requests.
Supports graceful shutdown, health checks, automatic retries, and concurrent workers.

Usage:
    python worker_daemon.py [--worker-id WORKER_ID] [--redis-url REDIS_URL]

Environment Variables:
    REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    WORKER_ID: Unique worker identifier (default: auto-generated)
    MAX_RETRIES: Maximum retry attempts for failed jobs (default: 3)
    HEALTH_CHECK_INTERVAL: Seconds between health checks (default: 30)
"""

import asyncio
import json
import os
import signal
import sys
import time
import uuid
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from workers.account_creator import KickAccountCreator, AccountCreationError
from workers.utils import get_logger

# Initialize logger
logger = get_logger(__name__)

# Constants
QUEUE_KEY = "botrix:jobs:queue"
PROCESSING_KEY = "botrix:jobs:processing"
STATUS_KEY_PREFIX = "botrix:jobs:status:"
DATA_KEY_PREFIX = "botrix:jobs:data:"
RESULTS_KEY_PREFIX = "botrix:jobs:results:"
UPDATES_CHANNEL = "botrix:jobs:updates"
HEALTH_KEY_PREFIX = "botrix:worker:health:"

# Job statuses
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

# Configuration
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_MAX_RETRIES = 3
DEFAULT_HEALTH_CHECK_INTERVAL = 30
DEFAULT_JOB_TIMEOUT = 300  # 5 minutes
BLPOP_TIMEOUT = 5  # 5 seconds


class WorkerDaemon:
    """
    Worker daemon that processes account creation jobs from Redis queue
    """
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        redis_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        health_check_interval: int = DEFAULT_HEALTH_CHECK_INTERVAL
    ):
        """
        Initialize worker daemon
        
        Args:
            worker_id: Unique worker identifier
            redis_url: Redis connection URL
            max_retries: Maximum retry attempts for failed jobs
            health_check_interval: Seconds between health check updates
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.redis_url = redis_url or os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        self.max_retries = max_retries
        self.health_check_interval = health_check_interval
        
        # State
        self.running = False
        self.shutdown_requested = False
        self.current_job_id = None
        self.jobs_processed = 0
        self.jobs_succeeded = 0
        self.jobs_failed = 0
        self.start_time = None
        
        # Redis clients
        self.redis_client = None
        self.pubsub_client = None
        
        # Account creator
        self.account_creator = None
        
        # Health check task
        self.health_check_task = None
        
        logger.info(f"Initializing worker daemon: {self.worker_id}")
        logger.info(f"Redis URL: {self.redis_url}")
        logger.info(f"Max retries: {self.max_retries}")
        logger.info(f"Health check interval: {self.health_check_interval}s")
    
    def connect_redis(self) -> None:
        """Establish Redis connections"""
        try:
            logger.info(f"[{self.worker_id}] Connecting to Redis...")
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"[{self.worker_id}] Redis connection established")
            
        except RedisConnectionError as e:
            logger.error(f"[{self.worker_id}] Failed to connect to Redis: {e}")
            raise
    
    def disconnect_redis(self) -> None:
        """Close Redis connections"""
        if self.redis_client:
            try:
                # Remove health check entry
                health_key = f"{HEALTH_KEY_PREFIX}{self.worker_id}"
                self.redis_client.delete(health_key)
                
                self.redis_client.close()
                logger.info(f"[{self.worker_id}] Redis connection closed")
            except Exception as e:
                logger.warning(f"[{self.worker_id}] Error closing Redis: {e}")
    
    def update_health_check(self) -> None:
        """Update worker health check in Redis"""
        try:
            health_key = f"{HEALTH_KEY_PREFIX}{self.worker_id}"
            health_data = {
                "worker_id": self.worker_id,
                "status": "running" if self.running else "stopped",
                "last_heartbeat": datetime.utcnow().isoformat(),
                "current_job": self.current_job_id,
                "jobs_processed": self.jobs_processed,
                "jobs_succeeded": self.jobs_succeeded,
                "jobs_failed": self.jobs_failed,
                "uptime_seconds": int(time.time() - self.start_time) if self.start_time else 0,
            }
            
            # Set with 2x health check interval TTL
            self.redis_client.setex(
                health_key,
                self.health_check_interval * 2,
                json.dumps(health_data)
            )
            
            logger.debug(f"[{self.worker_id}] Health check updated")
            
        except Exception as e:
            logger.warning(f"[{self.worker_id}] Failed to update health check: {e}")
    
    async def health_check_loop(self) -> None:
        """Background task to update health check periodically"""
        logger.info(f"[{self.worker_id}] Starting health check loop")
        
        while self.running and not self.shutdown_requested:
            try:
                self.update_health_check()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                logger.info(f"[{self.worker_id}] Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"[{self.worker_id}] Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_msg: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update job status in Redis and publish update
        
        Args:
            job_id: Job identifier
            status: New status
            error_msg: Error message if failed
            result: Job result data
        """
        try:
            status_key = f"{STATUS_KEY_PREFIX}{job_id}"
            
            # Update status
            self.redis_client.set(status_key, status)
            
            # Store error message if failed
            if error_msg:
                error_key = f"{STATUS_KEY_PREFIX}{job_id}:error"
                self.redis_client.set(error_key, error_msg)
            
            # Store result if completed
            if result:
                results_key = f"{RESULTS_KEY_PREFIX}{job_id}"
                self.redis_client.set(results_key, json.dumps(result))
            
            # Publish update to channel
            update_data = {
                "job_id": job_id,
                "status": status,
                "worker_id": self.worker_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            if error_msg:
                update_data["error"] = error_msg
            
            if result:
                update_data["result"] = result
            
            self.redis_client.publish(UPDATES_CHANNEL, json.dumps(update_data))
            
            logger.info(f"[{self.worker_id}] Job {job_id} status updated to '{status}'")
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Failed to update job status: {e}")
    
    async def process_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Process a single job
        
        Args:
            job_data: Job data from queue
            
        Returns:
            True if successful, False otherwise
        """
        job_id = job_data.get("id")
        if not job_id:
            logger.error(f"[{self.worker_id}] Job missing ID: {job_data}")
            return False
        
        self.current_job_id = job_id
        retry_count = job_data.get("retry_count", 0)
        
        logger.info(f"[{self.worker_id}] Processing job {job_id} (retry: {retry_count}/{self.max_retries})")
        
        try:
            # Update status to running
            self.update_job_status(job_id, STATUS_RUNNING)
            
            # Initialize account creator if needed
            if not self.account_creator:
                self.account_creator = KickAccountCreator()
            
            # Extract job parameters
            count = job_data.get("count", 1)
            username = job_data.get("username")
            password = job_data.get("password")
            
            # Process account creation
            logger.info(f"[{self.worker_id}] Creating {count} account(s) for job {job_id}")
            
            # Create account(s)
            accounts_created = []
            errors = []
            
            for i in range(count):
                try:
                    logger.info(f"[{self.worker_id}] Creating account {i+1}/{count} for job {job_id}")
                    
                    # Create account (this is synchronous, wrap in executor if needed)
                    account_data = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.account_creator.create_account,
                        username,
                        password
                    )
                    
                    if account_data:
                        accounts_created.append(account_data)
                        logger.info(f"[{self.worker_id}] Account created: {account_data.get('username')}")
                    else:
                        error_msg = f"Account creation returned None for iteration {i+1}"
                        errors.append(error_msg)
                        logger.warning(f"[{self.worker_id}] {error_msg}")
                        
                except AccountCreationError as e:
                    error_msg = f"Account {i+1} failed: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"[{self.worker_id}] {error_msg}")
                except Exception as e:
                    error_msg = f"Unexpected error for account {i+1}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"[{self.worker_id}] {error_msg}", exc_info=True)
            
            # Determine final status
            if len(accounts_created) == count:
                # All accounts created successfully
                result = {
                    "accounts_created": len(accounts_created),
                    "accounts": accounts_created,
                    "completed_at": datetime.utcnow().isoformat(),
                }
                self.update_job_status(job_id, STATUS_COMPLETED, result=result)
                self.jobs_succeeded += 1
                logger.info(f"[{self.worker_id}] Job {job_id} completed successfully ({len(accounts_created)} accounts)")
                return True
                
            elif len(accounts_created) > 0:
                # Partial success
                result = {
                    "accounts_created": len(accounts_created),
                    "accounts": accounts_created,
                    "errors": errors,
                    "completed_at": datetime.utcnow().isoformat(),
                }
                error_msg = f"Partial success: {len(accounts_created)}/{count} accounts created"
                self.update_job_status(job_id, STATUS_COMPLETED, error_msg=error_msg, result=result)
                self.jobs_succeeded += 1
                logger.warning(f"[{self.worker_id}] Job {job_id} partially completed")
                return True
                
            else:
                # Total failure - check if we should retry
                if retry_count < self.max_retries:
                    logger.warning(f"[{self.worker_id}] Job {job_id} failed, requeueing (retry {retry_count + 1}/{self.max_retries})")
                    
                    # Requeue with incremented retry count
                    job_data["retry_count"] = retry_count + 1
                    self.redis_client.rpush(QUEUE_KEY, json.dumps(job_data))
                    
                    self.update_job_status(job_id, STATUS_PENDING)
                    return False
                else:
                    # Max retries reached
                    error_msg = f"All accounts failed after {self.max_retries} retries. Errors: {'; '.join(errors)}"
                    self.update_job_status(job_id, STATUS_FAILED, error_msg=error_msg)
                    self.jobs_failed += 1
                    logger.error(f"[{self.worker_id}] Job {job_id} failed permanently")
                    return False
                    
        except Exception as e:
            error_msg = f"Unexpected error processing job: {str(e)}"
            logger.error(f"[{self.worker_id}] {error_msg}", exc_info=True)
            
            # Check retry count
            if retry_count < self.max_retries:
                logger.warning(f"[{self.worker_id}] Requeueing job {job_id} after error (retry {retry_count + 1}/{self.max_retries})")
                job_data["retry_count"] = retry_count + 1
                self.redis_client.rpush(QUEUE_KEY, json.dumps(job_data))
                self.update_job_status(job_id, STATUS_PENDING)
            else:
                self.update_job_status(job_id, STATUS_FAILED, error_msg=error_msg)
                self.jobs_failed += 1
            
            return False
            
        finally:
            self.current_job_id = None
            self.jobs_processed += 1
    
    async def work_loop(self) -> None:
        """Main worker loop that processes jobs from queue"""
        logger.info(f"[{self.worker_id}] Starting work loop")
        
        while self.running and not self.shutdown_requested:
            try:
                # BLPOP with timeout (blocking pop from left of list)
                result = self.redis_client.blpop(QUEUE_KEY, timeout=BLPOP_TIMEOUT)
                
                if result is None:
                    # Timeout, no job available
                    logger.debug(f"[{self.worker_id}] No jobs in queue, waiting...")
                    continue
                
                # Result is tuple: (queue_name, job_data)
                _, job_json = result
                
                try:
                    job_data = json.loads(job_json)
                except json.JSONDecodeError as e:
                    logger.error(f"[{self.worker_id}] Invalid job JSON: {e}")
                    continue
                
                # Process the job
                await self.process_job(job_data)
                
            except RedisConnectionError as e:
                logger.error(f"[{self.worker_id}] Redis connection error: {e}")
                logger.info(f"[{self.worker_id}] Attempting to reconnect in 5 seconds...")
                await asyncio.sleep(5)
                try:
                    self.connect_redis()
                except Exception as reconnect_error:
                    logger.error(f"[{self.worker_id}] Reconnection failed: {reconnect_error}")
                    
            except asyncio.CancelledError:
                logger.info(f"[{self.worker_id}] Work loop cancelled")
                break
                
            except Exception as e:
                logger.error(f"[{self.worker_id}] Unexpected error in work loop: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"[{self.worker_id}] Work loop stopped")
    
    def handle_shutdown(self, signum, frame) -> None:
        """
        Handle shutdown signals (SIGTERM, SIGINT)
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"[{self.worker_id}] Received {signal_name}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def run(self) -> None:
        """Run the worker daemon"""
        logger.info(f"[{self.worker_id}] Starting worker daemon")
        self.start_time = time.time()
        self.running = True
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        try:
            # Connect to Redis
            self.connect_redis()
            
            # Start health check loop
            self.health_check_task = asyncio.create_task(self.health_check_loop())
            
            # Start work loop
            await self.work_loop()
            
        except KeyboardInterrupt:
            logger.info(f"[{self.worker_id}] Keyboard interrupt received")
        except Exception as e:
            logger.error(f"[{self.worker_id}] Fatal error: {e}", exc_info=True)
        finally:
            # Cleanup
            logger.info(f"[{self.worker_id}] Shutting down...")
            self.running = False
            
            # Cancel health check task
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect from Redis
            self.disconnect_redis()
            
            # Print statistics
            uptime = int(time.time() - self.start_time) if self.start_time else 0
            logger.info(f"[{self.worker_id}] Worker statistics:")
            logger.info(f"  - Uptime: {uptime}s")
            logger.info(f"  - Jobs processed: {self.jobs_processed}")
            logger.info(f"  - Jobs succeeded: {self.jobs_succeeded}")
            logger.info(f"  - Jobs failed: {self.jobs_failed}")
            
            logger.info(f"[{self.worker_id}] Worker daemon stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Botrix Worker Daemon - Process account creation jobs from Redis queue"
    )
    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Unique worker identifier (default: auto-generated)"
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default=None,
        help=f"Redis connection URL (default: {DEFAULT_REDIS_URL})"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum retry attempts for failed jobs (default: {DEFAULT_MAX_RETRIES})"
    )
    parser.add_argument(
        "--health-check-interval",
        type=int,
        default=DEFAULT_HEALTH_CHECK_INTERVAL,
        help=f"Seconds between health checks (default: {DEFAULT_HEALTH_CHECK_INTERVAL})"
    )
    
    args = parser.parse_args()
    
    # Create and run worker
    worker = WorkerDaemon(
        worker_id=args.worker_id,
        redis_url=args.redis_url,
        max_retries=args.max_retries,
        health_check_interval=args.health_check_interval
    )
    
    # Run the worker
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
