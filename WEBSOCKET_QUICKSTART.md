# WebSocket Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Start the Backend

```powershell
cd c:\Users\Cha0s\Desktop\Botrix\backend
go run main.go
```

You should see:
```
[WebSocket] Subscribed to Redis channel: botrix:jobs:updates
Server starting on :8080
```

### Step 2: Open the Test Client

Double-click or open in browser:
```
c:\Users\Cha0s\Desktop\Botrix\test_websocket.html
```

Click **Connect** button. You'll see:
```
✅ Connected to WebSocket server
```

### Step 3: Test Real-Time Updates

Open a new terminal and run:

```powershell
python test_websocket_publish.py
```

**Interactive commands:**
- Press `1` - Send "processing" update
- Press `2` - Send "completed" update  
- Press `3` - Send "failed" update
- Press `b` - Burst mode (5 updates)
- Press `s` - Stress test (20 updates)
- Press `q` - Quit

Watch the browser update in real-time! 🎉

## 📊 What You'll See

### In the Browser
- Live message log with timestamps
- Connection status indicator (green = connected)
- Message counters (total messages, job updates, errors)
- Uptime counter
- Formatted job updates with status colors

### In the Backend Logs
```
[WebSocket] Client registered: 20251107143000-abc123 (Total: 1)
[WebSocket] Broadcasted update for job 550e8400-... (status: completed) to 1 clients
```

### In the Python Script
```
✅ Published job update to 'botrix:jobs:updates'
📊 Status: completed
🆔 Job ID: 550e8400-e29b-41d4-a716-446655440000
👥 Active subscribers: 1
```

## 🧪 Quick Tests

### Test 1: Single Update
```powershell
python test_websocket_publish.py completed
```

### Test 2: Custom Job ID
```powershell
python test_websocket_publish.py processing my-custom-job-123
```

### Test 3: Multiple Updates
```powershell
python test_websocket_publish.py multi 5 2
# Sends 5 updates with 2-second delay
```

### Test 4: Stress Test
```powershell
python test_websocket_publish.py multi 20 0.5
# Sends 20 updates rapidly
```

### Test 5: Manual Redis Publish
```powershell
redis-cli
PUBLISH botrix:jobs:updates '{"job_id":"manual-test","status":"completed","data":{"test":true}}'
```

## 🔧 Integration with Python Worker

The Python worker already publishes to Redis! Just modify `workers/worker_daemon.py`:

```python
# Already implemented in update_job_status method:
await self.redis_client.publish(
    "botrix:jobs:updates",
    json.dumps({
        "job_id": job_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "data": result or {}
    })
)
```

No changes needed! When workers process jobs, WebSocket clients get instant updates.

## 📱 Connect from Your Own App

### JavaScript
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    console.log(`Job ${msg.job_id}: ${msg.status}`);
};
```

### Python
```python
import asyncio
import websockets

async def listen():
    async with websockets.connect('ws://localhost:8080/ws') as ws:
        async for message in ws:
            print(message)

asyncio.run(listen())
```

### cURL (Test Connection)
```powershell
# Install websocat first: scoop install websocat
websocat ws://localhost:8080/ws
```

## ❓ Common Issues

### Issue: "Connection refused"
**Fix:** Make sure backend is running (`go run main.go`)

### Issue: "No active subscribers"
**Fix:** Connect WebSocket client first, then publish messages

### Issue: "Redis connection error"
**Fix:** Start Redis:
```powershell
docker run -d -p 6379:6379 redis:7-alpine
```

### Issue: Browser can't connect
**Fix:** Check firewall, use `http://localhost:8080` not `https://`

## 🎯 Next Steps

1. **Integrate with Frontend:**
   - Copy WebSocket code to your React/Vue/Angular app
   - Display real-time job progress
   - Show notifications on completion

2. **Add Authentication:**
   - Add JWT token validation
   - See `WEBSOCKET_DOCUMENTATION.md` for implementation

3. **Deploy to Production:**
   - Use `wss://` (secure WebSocket)
   - Configure nginx reverse proxy
   - Add connection limits

4. **Monitor Performance:**
   - Check `/ws/stats` endpoint
   - Monitor backend logs
   - Use Redis `MONITOR` command

## 📚 More Information

- Full documentation: `WEBSOCKET_DOCUMENTATION.md`
- Worker integration: `WORKER_INTEGRATION_GUIDE.md`
- API reference: Backend API docs

## 💡 Pro Tips

1. **Keep browser console open** to see detailed WebSocket logs
2. **Use burst mode** (`b` in interactive) to test multiple clients
3. **Check `/ws/stats`** to see connected client count:
   ```powershell
   curl http://localhost:8080/ws/stats
   ```
4. **Monitor Redis** to see published messages:
   ```bash
   redis-cli MONITOR | grep "botrix:jobs:updates"
   ```

---

**That's it!** You now have real-time WebSocket updates working. 🎉

Any questions? Check the full docs or open an issue.
