#!/bin/bash
# Test different proxy layers by creating jobs and checking results

API_BASE="http://localhost:8000/api"
TEST_QUERY="What is the best ecommerce platform in 2026?"

echo "🧪 Testing Proxy Layers for UK Scraping (Async Jobs)"
echo "===================================================="
echo "Test Query: $TEST_QUERY"
echo ""

# Test 1: Direct VPN (free)
echo "1️⃣ Creating test job with DIRECT VPN (free)..."
response1=$(curl -s -X POST "${API_BASE}/jobs/scrape" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"$TEST_QUERY\",
        \"country\": \"uk\",
        \"scraper_type\": \"google_ai\",
        \"proxy_layer\": \"direct\",
        \"num_results\": 3,
        \"take_screenshot\": true
    }")

job1_id=$(echo "$response1" | grep -o '"job_id":[^,}]*' | cut -d':' -f2 | tr -d ' "')
if [ -n "$job1_id" ]; then
    echo "   ✅ Job created: ID $job1_id"
    echo "   ⏳ Waiting 30 seconds for job to complete..."
    sleep 30
    status1=$(curl -s "${API_BASE}/jobs/$job1_id" 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    echo "   Status: $status1"
    if [ "$status1" = "completed" ]; then
        DIRECT_WORKS=true
        echo "   ✅ DIRECT VPN: SUCCESS"
    else
        DIRECT_WORKS=false
        echo "   ❌ DIRECT VPN: Status is $status1"
    fi
else
    echo "   ❌ Failed to create job"
    DIRECT_WORKS=false
fi

echo ""

# Test 2: Unlocker (paid)
echo "2️⃣ Creating test job with UNLOCKER (~\$0.008/request)..."
response2=$(curl -s -X POST "${API_BASE}/jobs/scrape" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"$TEST_QUERY\",
        \"country\": \"uk\",
        \"scraper_type\": \"google_ai\",
        \"proxy_layer\": \"unlocker\",
        \"num_results\": 3,
        \"take_screenshot\": true
    }")

job2_id=$(echo "$response2" | grep -o '"job_id":[^,}]*' | cut -d':' -f2 | tr -d ' "')
if [ -n "$job2_id" ]; then
    echo "   ✅ Job created: ID $job2_id"
    echo "   ⏳ Waiting 30 seconds for job to complete..."
    sleep 30
    status2=$(curl -s "${API_BASE}/jobs/$job2_id" 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    echo "   Status: $status2"
    if [ "$status2" = "completed" ]; then
        UNLOCKER_WORKS=true
        echo "   ✅ UNLOCKER: SUCCESS"
    else
        UNLOCKER_WORKS=false
        echo "   ❌ UNLOCKER: Status is $status2"
    fi
else
    echo "   ❌ Failed to create job"
    UNLOCKER_WORKS=false
fi

echo ""

# Test 3: Browser (paid)
echo "3️⃣ Creating test job with BROWSER (~\$0.025/request)..."
response3=$(curl -s -X POST "${API_BASE}/jobs/scrape" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"$TEST_QUERY\",
        \"country\": \"uk\",
        \"scraper_type\": \"google_ai\",
        \"proxy_layer\": \"browser\",
        \"num_results\": 3,
        \"take_screenshot\": true
    }")

job3_id=$(echo "$response3" | grep -o '"job_id":[^,}]*' | cut -d':' -f2 | tr -d ' "')
if [ -n "$job3_id" ]; then
    echo "   ✅ Job created: ID $job3_id"
    echo "   ⏳ Waiting 30 seconds for job to complete..."
    sleep 30
    status3=$(curl -s "${API_BASE}/jobs/$job3_id" 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    echo "   Status: $status3"
    if [ "$status3" = "completed" ]; then
        BROWSER_WORKS=true
        echo "   ✅ BROWSER: SUCCESS"
    else
        BROWSER_WORKS=false
        echo "   ❌ BROWSER: Status is $status3"
    fi
else
    echo "   ❌ Failed to create job"
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
    echo "⏳ Jobs are still running. Check status later:"
    echo "   curl ${API_BASE}/jobs/$job1_id"
    echo "   curl ${API_BASE}/jobs/$job2_id"
    echo "   curl ${API_BASE}/jobs/$job3_id"
    RECOMMENDED="check_later"
fi

echo ""
if [ "$RECOMMENDED" != "check_later" ]; then
    echo "💡 Recommended proxy layer: $RECOMMENDED"
    echo ""
    echo "To update all UK daily jobs to use $RECOMMENDED:"
    echo "   bash scripts/update_uk_jobs_proxy.sh $RECOMMENDED"
fi
