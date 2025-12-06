#!/bin/bash

# Configuration
BASE_URL="http://localhost:80/api"
USERNAME="admin"
PASSWORD="adminpassword"  # Replace with your actual admin password

echo "---------------------------------------------------"
echo "1. Authenticating (Getting JWT Token)..."
echo "---------------------------------------------------"

# Get Token
RESPONSE=$(curl -s -X POST "$BASE_URL/token/" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

# Extract Access Token (requires jq, or simplistic grep/sed)
if command -v jq &> /dev/null; then
    ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access')
else
    # Fallback for when jq is not installed (simple regex)
    ACCESS_TOKEN=$(echo $RESPONSE | grep -o '"access":"[^"]*' | cut -d'"' -f4)
fi

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo "Authentication Failed!"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "Token successfully obtained."
echo "Access Token: ${ACCESS_TOKEN:0:20}..." # Show truncated token

echo ""
echo "---------------------------------------------------"
echo "2. Listing Admin Users (GET /admins/)..."
echo "---------------------------------------------------"

curl -s -X GET "$BASE_URL/admins/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" | python3 -m json.tool || echo "Failed to list admins (or python not installed for formatting)"

echo ""
echo "---------------------------------------------------"
echo "3. Creating a New Admin User (POST /admins/)..."
echo "---------------------------------------------------"

# Random username to avoid conflict on re-runs
NEW_USER="api_test_user_$(date +%s)"

CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/admins/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$NEW_USER\",
    \"password\": \"TestPass123!\",
    \"is_staff\": true
  }")

echo "Response:"
echo $CREATE_RESPONSE

# Extract ID of new user
if command -v jq &> /dev/null; then
    NEW_USER_ID=$(echo $CREATE_RESPONSE | jq -r '.id')
else
    NEW_USER_ID=$(echo $CREATE_RESPONSE | grep -o '"id":[^,]*' | cut -d':' -f2 | tr -d ' ')
fi

if [ -z "$NEW_USER_ID" ] || [ "$NEW_USER_ID" == "null" ]; then
    echo "Failed to create user."
    # Continue anyway to show other endpoints structure
else
    echo "Created User ID: $NEW_USER_ID"
    
    echo ""
    echo "---------------------------------------------------"
    echo "4. Retrieving the New Admin User (GET /admins/$NEW_USER_ID/)..."
    echo "---------------------------------------------------"

    curl -s -X GET "$BASE_URL/admins/$NEW_USER_ID/" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json"

    echo ""
    echo "---------------------------------------------------"
    echo "5. Updating the Admin User (PUT /admins/$NEW_USER_ID/)..."
    echo "---------------------------------------------------"
    
    # Example: Change is_active status
    curl -s -X PUT "$BASE_URL/admins/$NEW_USER_ID/" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"$NEW_USER\",
        \"is_active\": false
      }"

    echo ""
    echo "---------------------------------------------------"
    echo "6. Deleting the Admin User (DELETE /admins/$NEW_USER_ID/)..."
    echo "---------------------------------------------------"

    curl -s -X DELETE "$BASE_URL/admins/$NEW_USER_ID/" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json"
      
    echo "Delete request sent (204 No Content expected on success)."
fi

echo ""
echo "---------------------------------------------------"
echo "Test Script Completed."
echo "---------------------------------------------------"
