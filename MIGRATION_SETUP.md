# Database Migration Setup Guide

Alembic has been configured for database migrations. Follow these steps to set up and use migrations.

## Installation

1. Install the new dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Initial Setup

### Option A: You have an existing database (recommended)

If you already have a database with tables:

1. **Generate the initial migration** (this captures your current schema):
   ```bash
   python scripts/migrate.py revision --autogenerate -m "Initial schema"
   ```

2. **Review the generated migration** in `alembic/versions/` - make sure it matches your current schema

3. **Mark your database as migrated** (this tells Alembic your DB is already at this state):
   ```bash
   python scripts/migrate.py stamp head
   ```

4. **Verify** the current state:
   ```bash
   python scripts/migrate.py current
   ```

### Option B: Starting fresh

If you're starting with a new database:

1. **Generate the initial migration**:
   ```bash
   python scripts/migrate.py revision --autogenerate -m "Initial schema"
   ```

2. **Review the generated migration** in `alembic/versions/`

3. **Apply the migration** to create all tables:
   ```bash
   python scripts/migrate.py upgrade head
   ```

## Making Schema Changes

When you modify your models:

1. **Make your model changes** in `infra/database/models/`

2. **Generate a migration**:
   ```bash
   python scripts/migrate.py revision --autogenerate -m "Description of your changes"
   ```

3. **Review the generated migration** - Alembic might miss some changes, so check:
   - Indexes
   - Constraints
   - Column renames (Alembic treats these as drop+add)
   - Data migrations (if you need to transform data)

4. **Edit the migration** if needed (add missing indexes, data transformations, etc.)

5. **Test the migration**:
   ```bash
   # Apply
   python scripts/migrate.py upgrade head
   
   # If something goes wrong, rollback
   python scripts/migrate.py downgrade -1
   ```

## Common Commands

```bash
# Show current migration version
python scripts/migrate.py current

# Show migration history
python scripts/migrate.py history

# Apply all pending migrations
python scripts/migrate.py upgrade head

# Apply next migration
python scripts/migrate.py upgrade +1

# Rollback one migration
python scripts/migrate.py downgrade -1

# Rollback to specific revision
python scripts/migrate.py downgrade <revision_id>

# Create new migration (auto-generate)
python scripts/migrate.py revision --autogenerate -m "Your message"

# Create empty migration
python scripts/migrate.py revision -m "Your message"
```

## Environment Configuration

The migration system reads `DATABASE_URL` from your environment. Make sure it's set in your `.env` file:

```bash
# Development (SQLite)
DATABASE_URL=sqlite:///./app.db

# Production (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname
```

## Migration Files

- Migration files are stored in `alembic/versions/`
- Each migration has a unique revision ID
- Never edit migrations that have been applied to production
- Always review auto-generated migrations before applying

## Best Practices

1. **Always review** auto-generated migrations before applying
2. **Test migrations** on a copy of production data if possible
3. **Never edit** migrations that have been applied to production
4. **Use descriptive messages** when creating migrations
5. **Commit migration files** to version control
6. **Run migrations** as part of your deployment process

## Troubleshooting

### Migration conflicts
If you have conflicts between branches:
- Merge migrations carefully
- You may need to create a new migration to reconcile differences

### Migration fails
- Check the error message
- Rollback: `python scripts/migrate.py downgrade -1`
- Fix the migration file
- Re-apply: `python scripts/migrate.py upgrade head`

### Database out of sync
- Check current version: `python scripts/migrate.py current`
- Check history: `python scripts/migrate.py history`
- You may need to stamp the database: `python scripts/migrate.py stamp <revision>`

