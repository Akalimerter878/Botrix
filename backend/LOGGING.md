# Backend Logging System

## Overview

Botrix backend'i gelişmiş, renkli ve yapılandırılmış bir loglama sistemi kullanır. Bu sistem hem konsola hem de dosyaya loglama yapabilir.

## Log Seviyeleri

| Seviye | Renk | Kullanım |
|--------|------|----------|
| DEBUG | Cyan | Detaylı debug bilgileri |
| INFO | Green | Genel bilgilendirme mesajları |
| WARN | Yellow | Uyarı mesajları |
| ERROR | Red | Hata mesajları |
| FATAL | Magenta | Fatal hatalar (uygulama sonlanır) |

## Özellikler

### 1. **Renkli Console Output**
Terminal çıktısı ANSI renk kodları ile renklendirilir, daha kolay okunabilir.

### 2. **Dosyaya Loglama**
Tüm loglar `./logs/botrix-YYYY-MM-DD.log` formatında dosyaya kaydedilir.

### 3. **Structured Logging (Context Fields)**
```go
logger.WithField("user_id", 123).Info("User logged in")
logger.WithFields(map[string]interface{}{
    "job_id": "abc123",
    "status": "completed",
}).Info("Job finished")
```

### 4. **Component-Based Logging**
Her bileşen kendi logger'ını oluşturabilir:
```go
dbLogger := logger.WithComponent("DATABASE")
dbLogger.Info("Database connected")
// Output: [INFO] [DATABASE] Database connected
```

### 5. **Caller Information**
Log mesajları hangi dosya ve satırdan geldiğini gösterir:
```go
logger.Info("Test message")
// Output: [INFO] [main.go:45] Test message
```

### 6. **Multiple Outputs**
Aynı anda hem console'a hem de dosyaya yazabilir:
```go
logger.AddOutput(customWriter)
```

## Kullanım Örnekleri

### Basit Kullanım
```go
import "botrix-backend/utils"

// Varsayılan logger kullanımı
utils.Info("Server started on port 8080")
utils.Warn("Configuration not found, using defaults")
utils.Error("Failed to connect to database: %v", err)
```

### Component Logger
```go
logger := utils.GetDefaultLogger()
apiLogger := logger.WithComponent("API")

apiLogger.Info("Handling request: %s", c.Path())
apiLogger.WithFields(map[string]interface{}{
    "method": c.Method(),
    "path":   c.Path(),
    "ip":     c.IP(),
}).Info("Request received")
```

### Context Fields
```go
logger.WithField("user_id", userID).Info("User action performed")

logger.WithFields(map[string]interface{}{
    "job_id":  jobID,
    "status":  "pending",
    "workers": 5,
}).Debug("Job created")
```

### Log Seviyesi Ayarlama
```go
logger.SetLevel(utils.DEBUG) // Development için
logger.SetLevel(utils.INFO)  // Production için
logger.SetLevel(utils.ERROR) // Sadece hataları logla
```

## Log Formatı

### Standart Format
```
TIMESTAMP [LEVEL] [COMPONENT] [FILE:LINE] MESSAGE | context_key=value
```

### Örnek Çıktı
```
2025-11-10 20:23:14.507 [INFO ] [STARTUP] [main.go:34] Starting Botrix Backend API...
2025-11-10 20:23:14.508 [INFO ] [DATABASE] [database.go:56] Database connected | driver=sqlite
2025-11-10 20:23:14.509 [DEBUG] [API] [middleware.go:45] Request received | method=GET path=/api/jobs ip=127.0.0.1
2025-11-10 20:23:14.520 [INFO ] [API] [middleware.go:78] ✓ Request completed successfully | status=200 latency=11ms
2025-11-10 20:23:14.521 [WARN ] [WEBSOCKET] [websocket.go:123] Client inactive for too long | client_id=xxx inactive=2m15s
2025-11-10 20:23:14.522 [ERROR] [QUEUE] [queue.go:89] Redis connection failed | error=connection refused
```

## Backend Bileşenleri ve Log Mesajları

### STARTUP
- `Starting Botrix Backend API...`
- `Environment: development/production`
- `Debug logging enabled`

### DATABASE
- `Database connected`
- `Migration completed`
- `Query executed`

### QUEUE
- `Connected to Redis`
- `Job published`
- `Job consumed`

### API (HTTP Requests)
- `→ Incoming request` - Gelen istek
- `✓ Request completed successfully` - Başarılı (200-399)
- `⚠ Request completed with client error` - Client hatası (400-499)
- `✗ Request completed with server error` - Server hatası (500+)

### WEBSOCKET
- `Subscribed to Redis channel`
- `Client registered` - Yeni WebSocket bağlantısı
- `Client unregistered` - WebSocket bağlantısı kapandı
- `Job update broadcasted` - İş güncellemesi gönderildi
- `Client inactive for too long` - İnaktif client disconnected

### RATELIMIT
- `New rate limit window` - Yeni zaman penceresi başladı
- `Rate limit check passed` - Rate limit kontrolü geçti
- `Rate limit exceeded` - Rate limit aşıldı

## Performans Notları

1. **Log Seviyeleri**: Production'da INFO veya WARN seviyesi kullanın
2. **Debug Logging**: Sadece development'ta DEBUG açın
3. **File Rotation**: Log dosyaları günlük olarak rotate edilir
4. **Async Logging**: Tüm loglar non-blocking şekilde yazılır

## Konfigürasyon

### Environment-Based Log Level
```go
if cfg.IsDevelopment() {
    logger.SetLevel(utils.DEBUG)
} else {
    logger.SetLevel(utils.INFO)
}
```

### Custom Log File Location
```go
logger, err := utils.InitFileLogger("./custom/logs", utils.INFO)
```

## WebSocket Connection Davranışı

**Normal Davranış**: WebSocket clientlar bağlanıp hemen kapanıyorsa bu normaldir!

Dashboard'un connection stratejisi:
1. Client bağlanır
2. Authentication/handshake yapar
3. Eğer aktif job yoksa bağlantıyı kapatır
4. İhtiyaç olduğunda tekrar bağlanır (reconnection strategy)

**Ne Zaman Endişelenmeli:**
- Eğer "Unexpected close error" görüyorsanız
- Eğer çok sayıda "slow consumer" uyarısı varsa
- Eğer Redis bağlantısı kopuyorsa

**Öneriler:**
1. WebSocket DEBUG logları için `logger.SetLevel(utils.DEBUG)` kullanın
2. Client disconnection'ları INFO seviyesinde, sadece hatalar ERROR'da
3. Ping/pong mesajları DEBUG seviyesinde

## Troubleshooting

### Çok Fazla Log
```go
logger.SetLevel(utils.WARN) // Sadece uyarı ve hataları göster
```

### Log Dosyası Bulunamıyor
```bash
mkdir -p ./logs
chmod 755 ./logs
```

### Renkler Görünmüyor
Terminal'in ANSI renk kodlarını desteklediğinden emin olun veya:
```go
logger.enableColor = false
```

## Best Practices

1. ✅ **Her bileşen kendi logger'ını oluştursun**
   ```go
   wsLogger := logger.WithComponent("WEBSOCKET")
   ```

2. ✅ **Context fields ile ek bilgi ekleyin**
   ```go
   logger.WithField("job_id", jobID).Info("Job started")
   ```

3. ✅ **Error'larda detaylı bilgi verin**
   ```go
   logger.WithFields(map[string]interface{}{
       "error": err.Error(),
       "retry": retryCount,
   }).Error("Operation failed")
   ```

4. ❌ **Sensitive data loglamayın**
   ```go
   // BAD
   logger.Info("Password: %s", password)
   
   // GOOD
   logger.Info("User authenticated")
   ```

5. ✅ **Production'da log seviyesini ayarlayın**
   ```go
   if cfg.IsProduction() {
       logger.SetLevel(utils.WARN)
   }
   ```
