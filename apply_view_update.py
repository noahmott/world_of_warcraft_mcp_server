"""
Apply the updated user_activity_summary view to Supabase
"""
import asyncio
import os
from dotenv import load_dotenv
from supabase import acreate_client

async def update_view():
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    # Read the SQL file
    with open("update_activity_summary_view.sql", "r") as f:
        sql = f.read()

    print(f"Connecting to Supabase at {url}...")
    supabase = await acreate_client(url, key)

    print("Applying view update...")
    try:
        # Execute the SQL using rpc
        result = await supabase.rpc("exec_sql", {"sql": sql}).execute()
        print("View updated successfully!")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTrying alternative method with postgrest...")
        # Postgrest doesn't support raw SQL, so we need to use psql or supabase dashboard
        print("\nPlease run this SQL in your Supabase SQL Editor:")
        print(sql)

if __name__ == "__main__":
    asyncio.run(update_view())
