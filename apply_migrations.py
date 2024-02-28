from dotenv import load_dotenv
load_dotenv()

import os
import db

migrations_dir = 'migrations'  # Relative directory path

# Get all migration files
migration_files = sorted(os.listdir(migrations_dir))

# Apply migrations in alphabetical order
for migration_file in migration_files:
  migration_path = os.path.join(migrations_dir, migration_file)
  print(f"* Applying migration: {migration_path}")

  with open(migration_path, 'r') as f:
    migration_sql = f.read()

  print(migration_sql)

  db.apply_migration(migration_sql)
  print(f"* Migration applied: {migration_path}")

print(f"* {len(migration_files)} migrations applied.")
