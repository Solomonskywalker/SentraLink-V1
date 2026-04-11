import os
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
from pathlib import Path
from trino.dbapi import connect
from trino.auth import BasicAuthentication
from pyopensky.trino import Trino

# 1. SETUP: Load credentials
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)


def run_daily_ingest():
    # 1. Use ONLY your website credentials
    # Ensure OS_USERNAME is 'skywalker1' and OS_PASSWORD is your web password
    user = os.getenv("OS_USERNAME").lower()
    password = os.getenv("OS_PASSWORD")
    db_url = os.getenv("DB_URL")

    if not password or not db_url:
        print(f"❌ Error: Missing credentials in {env_path}")
        return

    # Set environment variables for the pyopensky library
    os.environ['OPENSKY_USERNAME'] = user
    os.environ['OPENSKY_PASSWORD'] = password

    # 2. DATE LOGIC
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"🚀 Starting ingest for: {yesterday}")

    try:
        # 3. THE PROBE
        print(f"📡 Probing Trino permissions for user: {user}...")

        with connect(
                host="trino.opensky-network.org",
                port=443,
                http_scheme="https",
                auth=BasicAuthentication(user, password), # Use real password here
                user=user,
                catalog="osm",
                schema="default"
        ) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            print("✅ Authentication successful!")

        # 4. DUPLICATE CHECK
        engine = create_engine(db_url)
        try:
            check_query = f"SELECT COUNT(*) FROM daily_flights_archive WHERE day_recorded = '{yesterday}'"
            existing_count = pd.read_sql(check_query, engine).iloc[0, 0]
            if existing_count > 0:
                print(f"⚠️ Data for {yesterday} already exists ({existing_count} rows). Skipping.")
                return
        except Exception:
            pass  # Table doesn't exist yet

        # 5. MAIN QUERY
        # Re-initializing Trino with the hybrid credentials
        trino = Trino()

        query = f"""
            SELECT 
                icao24, callsign, origin_country, time, lastcontact, 
                lon, lat, baroaltitude, onground, velocity, 
                heading, vertrate, geoaltitude, squawk, spi, day
            FROM state_vectors_data4 
            WHERE day = '{yesterday}'
            AND hour = 12
            LIMIT 10000
        """

        print(f"📡 Fetching data for {yesterday}...")
        df = trino.query(query)

        if df is None or df.empty:
            print("❌ No data returned. Check account permissions for state_vectors_data4.")
            return

        # 6. SAVE TO POSTGRES
        df['day_recorded'] = yesterday
        df.to_sql(
            'daily_flights_archive',
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=500
        )

        print(f"✅ Success! Inserted {len(df)} flight records.")

    except Exception as e:
        print(f"💥 Error during ingest: {e}")


if __name__ == "__main__":
    run_daily_ingest()