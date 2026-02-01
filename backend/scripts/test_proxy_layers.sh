#!/bin/bash
# Test different proxy layers to find one that works reliably

API_BASE="http://localhost:8000/api"
TEST_QUERY="What is the best ecommerce platform in 2026?"

echo "🧪 Testing Proxy Layers for UK Scraping"
echo "========================================"
echo "Test Query: $TEST_QUERY"
echo ""

# Test 1: Direct VPN (free)
echo "1️⃣ Testing DIRECT VPN (free)..."
response1=$(curl -s -X POST "${API_BASE}/jobs/scrape" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"$TEST_QUERY\",
        \"country\": \"uk\",
        \"scraper_type\": \"google_ai\",
        \"proxy_layer\": \"direct\",
        \"num_results\": 3,
        \"take_screenshot\": true
    }" --max-time 120)

if echo "$response1" | grep -q '"status":"success"'; then
    echo "   ✅ DIRECT VPN: SUCCESS"
    DIRECT_WORKS=true
elif echo "$response1" | grep -q '"job_id"'; then
    job_id=$(echo "$response1" | grep -o '"job_id":[^,}]*' | cut -d':' -f2 | tr -d ' "')
    echo "   ⏳ DIRECT VPN: Job created (ID: $job_id), checking status..."
    sleep 5
    status=$(curl -s "${API_BASE}/jobs/$job_id" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$status" = "completed" ]; then
        echo "   ✅ DIRECT VPN: SUCCESS (job completed)"
        DIRECT_WORKS=true
    else
        echo "   ❌ DIRECT VPN: FAILED (status: $status)"
        DIRECT_WORKS=false
    fi
else
    echo "   ❌ DIRECT VPN: FAILED"
    echo "   Response: $response1"
    DIRECT_WORKS=false
fi

echo ""

# Test 2: Unlocker (paid, ~$0.008/req)
echo "2️⃣ Testing UNLOCKER (~\$0.008/request)..."
response2=$(curl -s -X POST "${API_BASE}/jobs/scrape" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"$TEST_QUERY\",
        \"country\": \"uk\",
        \"scraper_type\": \"google_ai\",
        \"proxy_layer\": \"unlocker\",
        \"num_results\": 3,
        \"take_screenshot\": true
    }" --max-time 120)

if echo "$response2" | grep -q '"status":"success"'; then
    echo "   ✅ UNLOCKER: SUCCESS"
    UNLOCKER_WORKS=true
elif echo "$response2" | grep -q '"job_id"'; then
    job_id=$(echo "$response2" | grep -o '"job_id":[^,}]*' | cut -d':' -f2 | tr -d ' "')
    echo "   ⏳ UNLOCKER: Job created (ID: $job_id), checking status..."
    sleep 5
    status=$(curl -s "${API_BASE}/jobs/$job_id" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$status" = "completed" ]; then
        echo "   ✅ UNLOCKER: SUCCESS (job completed)"
        UNLOCKER_WORKS=true
    else
        echo "   ❌ UNLOCKER: FAILED (status: $status)"
        UNLOCKER_WORKS=false
    fi
else
    echo "   ❌ UNLOCKER: FAILED"
    echo "   Response: $response2"
    UNLOCKER_WORKS=false
fi

echo ""

# Test 3: Browser (paid, ~$0.025/req)
echo "3️⃣ Testing BROWSER (~\$0.025/request)..."
response3=$(curl -s -X POST "${API_BASE}/jobs/scrape" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"$TEST_QUERY\",
        \"country\": \"uk\",
        \"scraper_type\": \"google_ai\",
        \"proxy_layer\": \"browser\",
        \"num_results\": 3,
        \"take_screenshot\": true
    }" --max-time 120)

if echo "$response3" | grep -q '"status":"success"'; then
    echo "   ✅ BROWSER: SUCCESS"
    BROWSER_WORKS=true
elif echo "$response3" | grep -q '"job_id"'; then
    job_id=$(echo "$response3" | grep -o '"job_id":[^,}]*' | cut -d':' -f2 | tr -d ' "')
    echo "   ⏳ BROWSER: Job created (ID: $job_id), checking status..."
    sleep 5
    status=$(curl -s "${API_BASE}/jobs/$job_id" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$status" = "completed" ]; then
        echo "   ✅ BROWSER: SUCCESS (job completed)"
        BROWSER_WORKS=true
    else
        echo "   ❌ BROWSER: FAILED (status: $status)"
        BROWSER_WORKS=false
    fi
else
    echo "   ❌ BROWSER: FAILED"
    echo "   Response: $response3"
    BROWSER_WORKS=false
fi

echo ""
echo "========================================"
echo "📊 TEST RESULTS SUMMARY"
echo "========================================"

if [ "$DIRECT_WORKS" = true ]; then
    echo "✅ DIRECT VPN: WORKS (FREE)"
    RECOMMENDED="direct"
elif [ "$UNLOCKER_WORKS" = true ]; then
    echo "✅ UNLOCKER: WORKS (~\$0.008/request)"
    RECOMMENDED="unlocker"
elif [ "$BROWSER_WORKS" = true ]; then
    echo "✅ BROWSER: WORKS (~\$0.025/request)"
    RECOMMENDED="browser"
else
    echo "❌ All methods failed - check VPN connectivity"
    RECOMMENDED="none"
fi

echo ""
echo "Recommended proxy layer: $RECOMMENDED"
echo ""

if [ "$RECOMMENDED" != "none" ]; then
    echo "💡 To update jobs to use $RECOMMENDED:"
    echo "   Run: bash scripts/update_jobs_proxy_layer.sh $RECOMMENDED"
fi
