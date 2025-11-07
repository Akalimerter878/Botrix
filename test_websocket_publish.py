#!/usr/bin/env python3
"""
WebSocket Test Script

This script publishes test messages to the Redis pub/sub channel
to verify WebSocket broadcasting is working correctly.

Usage:
    python test_websocket_publish.py [status] [job_id]

Examples:
    python test_websocket_publish.py processing
    python test_websocket_publish.py completed abc-123
    python test_websocket_publish.py failed xyz-789
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
import redis.asyncio as redis


# Redis configuration
REDIS_URL = "redis://localhost:6379/0"
UPDATES_CHANNEL = "botrix:jobs:updates"


async def publish_job_update(status: str = "processing", job_id: str = None):
    """
    Publish a test job update to Redis pub/sub channel.
    
    Args:
        status: Job status (processing, completed, failed)
        job_id: Optional job ID (auto-generated if not provided)
    """
    if job_id is None:
        job_id = str(uuid.uuid4())
    
    # Create test message
    message = {
        "job_id": job_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "event": "job_update",
        "data": {
            "job_id": job_id,
            "status": status,
        }
    }
    
    # Add status-specific data
    if status == "completed":
        message["data"]["result"] = {
            "accounts_created": 5,
            "success": True,
            "accounts": [
                {"username": f"test_user_{i}", "email": f"test{i}@example.com"}
                for i in range(1, 6)
            ]
        }
    elif status == "failed":
        message["data"]["error"] = "Sample error: Connection timeout"
        message["data"]["retry_count"] = 2
    elif status == "processing":
        message["data"]["progress"] = 50
        message["data"]["accounts_processed"] = 3
    
    # Connect to Redis
    print(f"📡 Connecting to Redis at {REDIS_URL}...")
    r = await redis.from_url(REDIS_URL, decode_responses=True)
    
    try:
        # Publish message
        message_json = json.dumps(message)
        subscribers = await r.publish(UPDATES_CHANNEL, message_json)
        
        print(f"✅ Published job update to '{UPDATES_CHANNEL}'")
        print(f"📊 Status: {status}")
        print(f"🆔 Job ID: {job_id}")
        print(f"👥 Active subscribers: {subscribers}")
        print(f"\n📋 Message:")
        print(json.dumps(message, indent=2))
        
        if subscribers == 0:
            print("\n⚠️  Warning: No subscribers listening to this channel!")
            print("   Make sure the Go backend is running and WebSocket handler is subscribed.")
        
    finally:
        await r.close()
        print("\n🔌 Redis connection closed")


async def publish_multiple_updates(count: int = 5, delay: float = 2.0):
    """
    Publish multiple test updates with delay between each.
    
    Args:
        count: Number of updates to publish
        delay: Delay in seconds between updates
    """
    statuses = ["processing", "processing", "completed", "failed", "processing"]
    
    for i in range(count):
        status = statuses[i % len(statuses)]
        print(f"\n{'='*60}")
        print(f"Publishing update {i+1}/{count}")
        print(f"{'='*60}")
        
        await publish_job_update(status=status)
        
        if i < count - 1:
            print(f"\n⏳ Waiting {delay} seconds before next update...")
            await asyncio.sleep(delay)


async def interactive_mode():
    """
    Interactive mode for publishing custom messages.
    """
    print("🎮 Interactive WebSocket Test Mode")
    print("="*60)
    print("Commands:")
    print("  1 - Send 'processing' update")
    print("  2 - Send 'completed' update")
    print("  3 - Send 'failed' update")
    print("  b - Burst mode (5 rapid updates)")
    print("  s - Stress test (20 updates)")
    print("  q - Quit")
    print("="*60)
    
    while True:
        choice = input("\nEnter command: ").strip().lower()
        
        if choice == 'q':
            print("👋 Goodbye!")
            break
        elif choice == '1':
            await publish_job_update(status="processing")
        elif choice == '2':
            await publish_job_update(status="completed")
        elif choice == '3':
            await publish_job_update(status="failed")
        elif choice == 'b':
            print("\n🚀 Burst mode: Sending 5 updates...")
            await publish_multiple_updates(count=5, delay=1.0)
        elif choice == 's':
            print("\n💥 Stress test: Sending 20 updates...")
            await publish_multiple_updates(count=20, delay=0.5)
        else:
            print("❌ Invalid command")


async def main():
    """Main entry point."""
    print("🧪 Botrix WebSocket Test Publisher")
    print("="*60)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        status = sys.argv[1]
        job_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        if status not in ["processing", "completed", "failed", "interactive", "multi"]:
            print(f"❌ Invalid status: {status}")
            print("Valid statuses: processing, completed, failed, interactive, multi")
            sys.exit(1)
        
        if status == "interactive":
            await interactive_mode()
        elif status == "multi":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            delay = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
            await publish_multiple_updates(count=count, delay=delay)
        else:
            await publish_job_update(status=status, job_id=job_id)
    else:
        # Default: interactive mode
        await interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
