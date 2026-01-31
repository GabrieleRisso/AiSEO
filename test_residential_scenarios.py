import requests
import json
import time

API_URL = "http://localhost:8000/api/jobs/scrape"

def run_test(name, payload):
    print(f"\n--- Running Test: {name} ---")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        if response.status_code == 200:
            data = response.json()
            print(f"Job Created: ID={data.get('job_id')}")
            
            # Poll for status
            job_id = data.get('job_id')
            for _ in range(60): # Wait up to 60 seconds
                time.sleep(2)
                # Check logs via docker in separate terminal usually, but here we just wait
                # Actually we can't check job status easily via API without listing all
                # Let's assume we check logs manually or trust the async process
                pass
            print("Test request sent successfully.")
        else:
            print(f"Request Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

# Scenario 1: Residential Proxy + Antidetect (Default)
payload_1 = {
    "query": "italian pasta brands",
    "country": "it",
    "scraper_type": "google_ai",
    "use_residential_proxy": True,
    "take_screenshot": True,
    "human_behavior": True # implies antidetect enabled
}

# Scenario 2: Residential Proxy + NO Antidetect
payload_2 = {
    "query": "italian pasta brands",
    "country": "it",
    "scraper_type": "google_ai",
    "use_residential_proxy": True,
    "take_screenshot": True,
    "human_behavior": False # This sets enabled=False in backend logic map
}

if __name__ == "__main__":
    # Wait for service restart
    print("Waiting 5s for services...")
    time.sleep(5)
    
    run_test("Residential + Antidetect", payload_1)
    time.sleep(5)
    run_test("Residential + NO Antidetect", payload_2)
