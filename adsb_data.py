import requests
from datetime import datetime
import time


# The conference areas
NODES = [
    {"name": "TC2_Cyprus", "lat": 35.15, "lon": 33.50, "dist": 250},
    {"name": "TC2_London", "lat": 51.50, "lon": -0.12, "dist": 250}
]
# Base URL for public geographic snapshots
BASE_URL = "https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{dist}"

def ingest_global_traffic(node):
    url = BASE_URL.format(lat=node['lat'], lon=node['lon'], dist=node['dist'])

    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json().get('ac', [])
        elif response.status_code == 429:
            return "Rate limit"
        else:
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def run_sentralink_V1():
    print("Sentralink Active........")
    while True:
        print(f"SentaLink Ingestion started. {datetime.now().strftime('%y-%m-%d %H:%M:%S')}")

        for node in NODES:
            attempt = 0
            success = False

            if attempt < 3 and not success:
                result = ingest_global_traffic(node)

                if result == "Rate limit":
                    time.sleep(30)
                    attempt +=1
                elif result is not None:
                    print(f"{node['name']}: Found {len(result)} aircraft")
                    success = True
                    # IMPORTANT: Be polite to the API between different regions
                    time.sleep(5)
                else:
                    print(f" {node['name']}: Node unreachable.")
                    break

        print(f"💤 Cycle complete. Next global check in 5 minutes...")
        time.sleep(300)


if __name__ == "__main__":
    run_sentralink_V1()
