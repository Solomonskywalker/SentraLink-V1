import requests
import psycopg2
from amadeus import Client, ResponseError
from datetime import datetime
import time
import os
import re
from dotenv import load_dotenv


# load the variable from file into the system
load_dotenv("/home/solomon/Documents/Software Engineering/SentraLink/V1/.env")
print("DB_NAME:", os.getenv("DB_NAME"))
print("DB_USER:", os.getenv("DB_USER"))
# Database parameters
DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv( "DB_HOST"),
    "port": os.getenv("DB_PORT")
}


def harvest_Cyprus():
    url = "https://opendata.adsb.fi/api/v3/lat/35.15/lon/33.50/dist/250"
    response = requests.get(url)
    print("status", response.status_code)
    print("Text",  response.text[:200])

    res = response.json()

    conn = psycopg2.connect(**DB_PARAMS)
    curr = conn.cursor()

    for ac in res.get('ac', []):
        icao = ac.get('hex')
        callsign = ac.get('flight', '').strip()
        lat = ac.get('lat')
        lon = ac.get('lon')
        alt = ac.get('alt_baro')
        gs = ac.get('gs')
        track = ac.get("track")

        # # 1. Fetch Route Enrichment
        # origin, dest = None, None
        # if callsign:
        #     origin, dest = get_route(callsign)


        # 2. Execute with exact column matching
        curr.execute("""
                INSERT INTO live_flights (
                    icao_hex, icao24, callsign, lat, lon, 
                    altitude_ft, baro_altitude, ground_speed_kts, track      
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (icao24, captured_at) DO NOTHING;
            """, (
            icao, icao, callsign, lat, lon,  str(alt), 0 if alt == "ground" else alt, gs, track
            # gs, origin, dest
        ))

    conn.commit()
    curr.close()
    conn.close()


if __name__ == '__main__':
    while True:
        print(f"{datetime.now()} Harvesting Cyprus Airspace...")
        harvest_Cyprus()
        time.sleep(300)



