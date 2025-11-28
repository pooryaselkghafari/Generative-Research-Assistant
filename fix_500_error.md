# Fix 500 Error - Migration Required

## Problem
The 500 error occurs because the database is missing the `keywords` and `target_journals` fields on the `Paper` model. The migration exists but hasn't been applied.

## Solution: Fix Migration Conflict First

**IMPORTANT**: There's a migration conflict that must be resolved first!

### Step 1: Create Merge Migration

The server has migration `0029_alter_subscriptionplan_options_and_more` that doesn't exist locally, creating a conflict. Run:

```bash
# On the server
docker-compose exec web python manage.py makemigrations --merge engine
```

This will create a merge migration (likely `0036_merge_0029_0035.py`) that resolves the conflict.

### Step 2: Run Migration

After creating the merge migration, run:

```bash
docker-compose exec web python manage.py migrate engine
```

## Solution: Run Migration

### Option 1: Using Docker Compose (Recommended for Production)

```bash
# SSH into your server
ssh deploy@your-server

# Navigate to project directory
cd /path/to/GRA

# Run the migration
docker-compose exec web python manage.py migrate engine

# Or if using a different container name:
docker-compose exec django python manage.py migrate engine
```

### Option 2: Direct Django Command

```bash
# If running Django directly (not in Docker)
python manage.py migrate engine
```

### Option 3: Run All Migrations

```bash
# Run all pending migrations
docker-compose exec web python manage.py migrate

# Or directly:
python manage.py migrate
```

## Verify Migration Applied

After running the migration, verify it worked:

```bash
# Check migration status
docker-compose exec web python manage.py showmigrations engine | grep 0035

# Should show: [X] 0035_add_keywords_journals_to_paper
```

## Restart Services

After migration, restart the web service:

```bash
docker-compose restart web
# or
docker-compose restart django
```

## Expected Result

After running the migration:
- ✅ The `keywords` and `target_journals` fields will be added to the `engine_paper` table
- ✅ Existing papers will have empty lists `[]` for these fields (safe default)
- ✅ The 500 error should be resolved
- ✅ The app should load normally after login

## Migration Details

The migration adds:
- `keywords`: JSONField (default: empty list `[]`)
- `target_journals`: JSONField (default: empty list `[]`)

Both fields are nullable and have safe defaults, so running this migration will not break existing data.

