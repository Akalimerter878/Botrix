# Backend Data Directory

This directory contains the SQLite database file when using SQLite as the database driver.

## Files

- **botrix.db**: Main SQLite database (auto-created on first run)
- **botrix.db-shm**: Shared memory file (SQLite internal)
- **botrix.db-wal**: Write-ahead log (SQLite internal)

## Switching to PostgreSQL

To use PostgreSQL instead, update backend/.env:

```bash
# Database configuration
DB_DRIVER=postgres
DB_HOST=localhost
DB_PORT=5432
DB_USER=botrix
DB_PASSWORD=your_password
DB_NAME=botrix
DB_SSLMODE=disable
```

Then start PostgreSQL:

```bash
# Using Docker
docker run -d \
  --name botrix-postgres \
  -e POSTGRES_DB=botrix \
  -e POSTGRES_USER=botrix \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:15-alpine

# Or use docker-compose
docker-compose up -d postgres
```

## Database Migrations

The backend automatically runs migrations on startup. Tables created:

- **accounts**: User account data
- **jobs**: Account creation job tracking

## Backup

### SQLite Backup

```bash
# Backup database
cp backend/data/botrix.db backend/data/botrix.db.backup

# Or use SQLite backup command
sqlite3 backend/data/botrix.db ".backup backend/data/botrix.db.backup"
```

### PostgreSQL Backup

```bash
# Backup database
pg_dump -U botrix -d botrix > backup.sql

# Restore
psql -U botrix -d botrix < backup.sql
```

## Security

**IMPORTANT**: Database files contain sensitive user data.
- Never commit .db files to git
- Keep backups secure and encrypted
- Use strong database passwords in production
