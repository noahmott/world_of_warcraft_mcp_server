"""
Apply user tracking migration to Supabase
"""
import asyncio
from supabase import acreate_client

SUPABASE_URL = "https://qctcrhhqnzbfmfamzunf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFjdGNyaGhxbnpiZm1mYW16dW5mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM1ODQzNzksImV4cCI6MjA2OTE2MDM3OX0.g4DZxrD8XMFXYBPUhVeRKZLfRsfSc3_cajnAsenXV1I"

async def apply_migration():
    """Apply the user tracking migration"""
    print("Connecting to Supabase...")
    client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)

    print("\nReading migration file...")
    with open("supabase/migrations/001_create_user_tracking_tables.sql", "r") as f:
        migration_sql = f.read()

    print("\nApplying migration...")
    print("Note: This uses the anon key, so some DDL operations may fail.")
    print("You may need to run this SQL directly in the Supabase SQL Editor.")
    print("\n" + "="*80)
    print("MIGRATION SQL TO RUN IN SUPABASE SQL EDITOR:")
    print("="*80)
    print(migration_sql)
    print("="*80)

    # Try to verify tables exist after manual application
    print("\n\nVerifying migration (run this after applying SQL in Supabase)...")
    try:
        # Check if users table exists
        result = await client.table("users").select("*").limit(1).execute()
        print("users table: OK")
    except Exception as e:
        print(f"users table: NOT FOUND - {e}")

    try:
        # Check if user_sessions table exists
        result = await client.table("user_sessions").select("*").limit(1).execute()
        print("user_sessions table: OK")
    except Exception as e:
        print(f"user_sessions table: NOT FOUND - {e}")

    try:
        # Check if activity_logs has new columns
        result = await client.table("activity_logs").select("user_id,session_id_ref,oauth_provider").limit(1).execute()
        print("activity_logs updated columns: OK")
    except Exception as e:
        print(f"activity_logs updated columns: NOT FOUND - {e}")

    await client.auth.sign_out()
    print("\n\nDone!")

if __name__ == "__main__":
    asyncio.run(apply_migration())
