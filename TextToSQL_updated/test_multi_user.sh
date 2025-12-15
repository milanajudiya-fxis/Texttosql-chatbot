#!/bin/bash

# Test conversation memory with multiple users
# Make sure the API server is running: python run_api.py

echo "=========================================="
echo "Testing Multi-User Conversation Memory"
echo "=========================================="

# User 1: Alice
echo -e "\n[User 1 - Alice] First message..."
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "My name is Alice and I work at Google", "thread_id": "user_alice"}' \
  -s | jq -r '.result' | head -c 100
echo "..."

sleep 1

# User 2: Bob
echo -e "\n\n[User 2 - Bob] First message..."
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "My name is Bob and I work at Microsoft", "thread_id": "user_bob"}' \
  -s | jq -r '.result' | head -c 100
echo "..."

sleep 1

# User 1: Ask about herself
echo -e "\n\n[User 1 - Alice] Follow-up question..."
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my name and where do I work?", "thread_id": "user_alice"}' \
  -s | jq -r '.result'

sleep 1

# User 2: Ask about himself
echo -e "\n\n[User 2 - Bob] Follow-up question..."
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my name and where do I work?", "thread_id": "user_bob"}' \
  -s | jq -r '.result'

sleep 1

# User 3: Charlie (new user, no context)
echo -e "\n\n[User 3 - Charlie] Asking about Alice..."
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Alice'\''s name?", "thread_id": "user_charlie"}' \
  -s | jq -r '.result' | head -c 150
echo "..."

echo -e "\n\n=========================================="
echo "Expected Results:"
echo "- Alice should remember: Google"
echo "- Bob should remember: Microsoft"
echo "- Charlie should NOT know about Alice"
echo "=========================================="
