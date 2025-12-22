"""Test multi-user conversation memory"""

import requests
import time

BASE_URL = "http://localhost:8010"

def send_message(thread_id, question):
    """Send a message and return the response"""
    response = requests.post(
        f"{BASE_URL}/query",
        json={"question": question, "thread_id": thread_id}
    )
    if response.status_code == 200:
        return response.json().get('result', 'No response')
    return f"Error: {response.status_code}"

def test_multi_user():
    print("=" * 60)
    print("Testing Multi-User Conversation Memory")
    print("=" * 60)
    
    # User 1: Alice
    print("\n[User 1 - Alice] Introducing herself...")
    response = send_message("user_alice", "number of games")
    print(f"Response: {response[:100]}...")
    
    time.sleep(1)
    
    # User 2: Bob
    print("\n[User 2 - Bob] Introducing himself...")
    response = send_message("user_bob", "is there basket ball game?")
    print(f"Response: {response[:100]}...")
    
    time.sleep(1)
    
    # User 3: Charlie
    print("\n[User 3 - Charlie] Introducing himself...")
    response = send_message("user_charlie", "what are is the max player in basket ball?")
    print(f"Response: {response[:100]}...")
    
    time.sleep(1)
    
    # Test memory for each user
    print("\n" + "=" * 60)
    print("Testing Memory Recall")
    print("=" * 60)
    
    print("\n[Alice] Asking about herself...")
    response = send_message("user_alice", "number of games")
    print(f"Response: {response}")
    if "alice" in response.lower() and "google" in response.lower():
        print("✓ Alice's memory working!")
    
    time.sleep(1)
    
    print("\n[Bob] Asking about himself...")
    response = send_message("user_bob", "is there basket ball game?")
    print(f"Response: {response}")
    if "bob" in response.lower() and "microsoft" in response.lower():
        print("✓ Bob's memory working!")
    
    time.sleep(1)
    
    print("\n[Charlie] Asking about himself...")
    response = send_message("user_charlie", "what are is the max player in basket ball?")
    print(f"Response: {response}")
    if "charlie" in response.lower() and "apple" in response.lower():
        print("✓ Charlie's memory working!")
    
    # Test thread isolation
    print("\n" + "=" * 60)
    print("Testing Thread Isolation")
    print("=" * 60)
    
    print("\n[Alice] Asking about Bob...")
    response = send_message("user_alice", "is there basket ball game?")
    print(f"Response: {response[:150]}...")
    if "bob" not in response.lower():
        print("✓ Thread isolation working - Alice doesn't know about Bob!")
    else:
        print("⚠ Warning: Alice seems to know about Bob (isolation may not be working)")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    print("\nMake sure the API server is running:")
    print("  python run_api.py")
    print("\nStarting test in 3 seconds...")
    time.sleep(3)
    
    try:
        test_multi_user()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("Please start the server with: python run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
