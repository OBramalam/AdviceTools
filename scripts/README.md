# Migration Scripts

## Running Migrations

Use the `migrate.py` script to manage database migrations:

```bash
# Apply all pending migrations
python scripts/migrate.py upgrade

# Apply next migration
python scripts/migrate.py upgrade +1

# Rollback one migration
python scripts/migrate.py downgrade -1

# Show current migration version
python scripts/migrate.py current

# Show migration history
python scripts/migrate.py history

# Mark database as being at a specific revision (useful for existing databases)
python scripts/migrate.py stamp head

# Create a new migration (auto-generate from model changes)
python scripts/migrate.py revision --autogenerate -m "Description of changes"

# Create an empty migration
python scripts/migrate.py revision -m "Description of changes"
```

## Initial Setup

If you have an existing database:

1. Generate the initial migration:
   ```bash
   python scripts/migrate.py revision --autogenerate -m "Initial schema"
   ```

2. Review the generated migration file in `alembic/versions/`

3. Mark your existing database as migrated (without applying changes):
   ```bash
   python scripts/migrate.py stamp head
   ```

If you're starting fresh:

1. Generate the initial migration:
   ```bash
   python scripts/migrate.py revision --autogenerate -m "Initial schema"
   ```

2. Apply the migration:
   ```bash
   python scripts/migrate.py upgrade head
   ```

## Environment Variables

Make sure you have `DATABASE_URL` set in your `.env` file:

```bash
# For SQLite (development)
DATABASE_URL=sqlite:///./app.db

# For PostgreSQL (production)
DATABASE_URL=postgresql://user:password@host:port/dbname
```

