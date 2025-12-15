"""Simple API test for conversation memory"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_api_conversation_memory():
    """Test conversation memory through API endpoints"""
    print("=" * 60)
    print("Testing API Conversation Memory")
    print("=" * 60)
    
    # Test 1: Send first message with thread_id
    print("\n[Test 1] Sending first message with thread_id...")
    response1 = requests.post(
        f"{BASE_URL}/query",
        json={
            "question": "My name is Alice and I work at Google",
            "thread_id": "api_test_user_1"
        }
    )
    
    if response1.status_code == 200:
        result1 = response1.json()
        print(f"✓ Status: {result1['success']}")
        print(f"  Response: {result1.get('result', 'N/A')[:100]}...")
    else:
        print(f"❌ Error: {response1.status_code}")
        return
    
    # Wait a bit
    time.sleep(2)
    
    # Test 2: Send follow-up question with same thread_id
    print("\n[Test 2] Sending follow-up question with same thread_id...")
    response2 = requests.post(
        f"{BASE_URL}/query",
        json={
            "question": "What is my name and where do I work?",
            "thread_id": "api_test_user_1"
        }
    )
    
    if response2.status_code == 200:
        result2 = response2.json()
        print(f"✓ Status: {result2['success']}")
        print(f"  Response: {result2.get('result', 'N/A')[:200]}...")
        
        # Check if response mentions Alice and Google
        response_text = result2.get('result', '').lower()
        if 'alice' in response_text:
            print("✓ Bot remembered the name 'Alice'")
        if 'google' in response_text:
            print("✓ Bot remembered the company 'Google'")
    else:
        print(f"❌ Error: {response2.status_code}")
        return
    
    # Test 3: Different thread should not have access to previous conversation
    print("\n[Test 3] Testing thread isolation with different thread_id...")
    response3 = requests.post(
        f"{BASE_URL}/query",
        json={
            "question": "What is my name?",
            "thread_id": "api_test_user_2"
        }
    )
    
    if response3.status_code == 200:
        result3 = response3.json()
        print(f"✓ Status: {result3['success']}")
        print(f"  Response: {result3.get('result', 'N/A')[:200]}...")
        
        response_text = result3.get('result', '').lower()
        if 'alice' not in response_text:
            print("✓ Thread isolation working - new thread doesn't know about Alice")
        else:
            print("⚠ Warning: Thread isolation may not be working properly")
    else:
        print(f"❌ Error: {response3.status_code}")
        return
    
    # Test 4: Query without thread_id (no memory)
    print("\n[Test 4] Testing query without thread_id (no memory)...")
    response4 = requests.post(
        f"{BASE_URL}/query",
        json={
            "question": "List all tables in the database"
        }
    )
    
    if response4.status_code == 200:
        result4 = response4.json()
        print(f"✓ Status: {result4['success']}")
        print(f"  Response: {result4.get('result', 'N/A')[:100]}...")
        print("✓ Query without thread_id works (stateless mode)")
    else:
        print(f"❌ Error: {response4.status_code}")
    
    print("\n" + "=" * 60)
    print("API tests completed! ✓")
    print("=" * 60)

if __name__ == "__main__":
    print("\nMake sure the API server is running:")
    print("  python run_api.py")
    print("\nPress Enter to continue...")
    input()
    
    try:
        test_api_conversation_memory()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("Please start the server with: python run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
