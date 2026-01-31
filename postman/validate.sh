#!/bin/bash
# Validate Postman collection and environment files

set -e

echo "Validating Postman files..."

# Check if files exist
if [ ! -f "AiSEO_API.postman_collection.json" ]; then
    echo "✗ Collection file not found"
    exit 1
fi

if [ ! -f "Local.postman_environment.json" ]; then
    echo "✗ Environment file not found"
    exit 1
fi

# Validate JSON syntax
echo "Validating JSON syntax..."
python3 -m json.tool AiSEO_API.postman_collection.json > /dev/null && echo "✓ Collection JSON is valid" || (echo "✗ Collection JSON is invalid" && exit 1)
python3 -m json.tool Local.postman_environment.json > /dev/null && echo "✓ Environment JSON is valid" || (echo "✗ Environment JSON is invalid" && exit 1)

# Check for required fields
echo "Validating collection structure..."
python3 << EOF
import json
import sys

with open('AiSEO_API.postman_collection.json', 'r') as f:
    collection = json.load(f)

# Check required fields
required_fields = ['info', 'item']
for field in required_fields:
    if field not in collection:
        print(f"✗ Missing required field: {field}")
        sys.exit(1)

# Check info fields
if 'name' not in collection['info']:
    print("✗ Missing 'name' in info")
    sys.exit(1)

print("✓ Collection structure is valid")
EOF

echo "✓ All validations passed!"
