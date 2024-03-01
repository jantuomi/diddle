from dotenv import load_dotenv
load_dotenv()

import os
import db

migrations_dir = 'migrations'  # Relative directory path

# Get all migration files
migration_files = sorted(os.listdir(migrations_dir))

db.ensure_migration_table_exists()

num_applied = 0

# Apply migrations in alphabetical order
for migration_file in migration_files:
  migration_path = os.path.join(migrations_dir, migration_file)
  print(f"* Applying migration: {migration_path}")

  with open(migration_path, 'r') as f:
    migration_sql = f.read()

  print(migration_sql)
  number = int(migration_file.split('_')[0])

  if db.ensure_migration_applied(number, migration_sql):
    print(f"* Migration applied: {migration_path}\n")
    num_applied += 1
  else:
    print(f"* Migration already applied: {migration_path}\n")

print(f"* {num_applied} migrations applied.")
