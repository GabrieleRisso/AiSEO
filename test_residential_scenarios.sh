#!/bin/bash

echo "--- Test 1: Residential + Antidetect (Default) ---"
curl -X POST "http://localhost:8000/api/jobs/scrape"      -H "Content-Type: application/json"      -d '{
        "query": "italian pasta brands", 
        "country": "it", 
        "scraper_type": "google_ai",
        "use_residential_proxy": true,
        "take_screenshot": true,
        "human_behavior": true
     }'
echo -e "\n"

sleep 5

echo "--- Test 2: Residential + NO Antidetect ---"
curl -X POST "http://localhost:8000/api/jobs/scrape"      -H "Content-Type: application/json"      -d '{
        "query": "italian pasta brands", 
        "country": "it", 
        "scraper_type": "google_ai",
        "use_residential_proxy": true,
        "take_screenshot": true,
        "human_behavior": false
     }'
echo -e "\n"
