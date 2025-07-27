# api_client.py

import json
import requests
from datetime import datetime, timedelta

from modular_bot import config

API_BASE_URL = "https://demo-api-capital.backend-capital.com"
API_HEADERS = {
    'X-CAP-API-KEY': config.api_key,
    'Content-Type': 'application/json'
}

xst = ""
cst = ""

def start_session():
    global xst, cst

    payload1 = json.dumps({
        "identifier": config.identifier,
        "password": config.password
    })
    headers1 = {
        'X-CAP-API-KEY': config.api_key,
        'Content-Type': 'application/json'
    }
    response1 = requests.request("POST", config.session_url, headers=headers1, data=payload1)

    if response1.status_code == 200:
        xst = response1.headers['X-SECURITY-TOKEN']
        cst = response1.headers['CST']
        print("started sesh")

# --- 2. Chunked Data Fetching Function ---
def fetch_all_data(epic, start_date, end_date):
    """
    Fetches all 15-minute data in chunks between a start and end date.
    """
    all_prices = []
    current_date = start_date
    start_session()
    print(f"Starting data fetch for {epic} from {start_date.isoformat()} to {end_date.isoformat()}")

    while current_date < end_date:
        # Format URL for the API call
        from_iso = current_date.isoformat()
        url = f"{API_BASE_URL}/api/v1/prices/{epic}?resolution=MINUTE_15&from={from_iso}&max=240"
        SESH_HEADERS = {
            'X-SECURITY-TOKEN': xst,
            'CST': cst
        }
        try:
            # In your real code, you would use your authenticated session
            response = requests.get(url, headers=SESH_HEADERS)
            response.raise_for_status()  # Raises an exception for bad responses (4xx or 5xx)

            data = response.json()
            prices = data.get('prices', [])

            if not prices:
                # No more data available in this range
                print("No more prices returned, ending fetch.")
                break

            all_prices.extend(prices)

            # Get the last timestamp and set it as the start for the next loop
            last_timestamp_str = prices[-1]['snapshotTimeUTC']
            last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', '+00:00'))

            print(f"Fetched {len(prices)} candles. Last timestamp: {last_timestamp.isoformat()}")

            # Move to the next chunk, adding 1 minute to avoid fetching the same candle twice
            current_date = last_timestamp + timedelta(minutes=1)

        except requests.exceptions.RequestException as e:
            print(f"An API error occurred: {e}")
            break

    print(f"Total candles fetched: {len(all_prices)}")
    return all_prices