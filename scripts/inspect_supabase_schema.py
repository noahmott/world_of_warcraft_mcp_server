"""
Inspect current Supabase schema and design user tracking tables
"""
import asyncio
import os
from supabase import acreate_client, AsyncClient

SUPABASE_URL = "https://qctcrhhqnzbfmfamzunf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFjdGNyaGhxbnpiZm1mYW16dW5mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM1ODQzNzksImV4cCI6MjA2OTE2MDM3OX0.g4DZxrD8XMFXYBPUhVeRKZLfRsfSc3_cajnAsenXV1I"

async def inspect_schema():
    """Inspect current Supabase schema"""
    client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)

    print("Checking existing tables...")

    # Check activity_logs table
    try:
        result = await client.table("activity_logs").select("*").limit(1).execute()
        print(f"\nactivity_logs table exists with columns: {result.data[0].keys() if result.data else 'No data yet'}")
    except Exception as e:
        print(f"\nactivity_logs table status: {e}")

    # Check for users table
    try:
        result = await client.table("users").select("*").limit(1).execute()
        print(f"\nusers table exists with columns: {result.data[0].keys() if result.data else 'No data yet'}")
    except Exception as e:
        print(f"\nusers table status: {e}")

    # Check for user_sessions table
    try:
        result = await client.table("user_sessions").select("*").limit(1).execute()
        print(f"\nuser_sessions table exists with columns: {result.data[0].keys() if result.data else 'No data yet'}")
    except Exception as e:
        print(f"\nuser_sessions table status: {e}")

    await client.auth.sign_out()
    print("\n\nSchema inspection complete!")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
