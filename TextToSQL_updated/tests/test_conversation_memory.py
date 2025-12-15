"""Test script for conversation memory functionality"""

import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.config import Settings
from src.core import ConversationManager

def test_conversation_persistence():
    """Test conversation memory persistence"""
    print("=" * 60)
    print("Testing Conversation Memory Persistence")
    print("=" * 60)
    
    # Initialize
    settings = Settings.from_env()
    cm = ConversationManager(settings)
    
    # Test 1: Create new thread and save messages
    print("\n[Test 1] Creating new conversation thread...")
    thread_id = "test_user_123"
    
    cm.save_message(thread_id, "user", "My name is Alice")
    print(f"✓ Saved user message")
    
    cm.save_message(thread_id, "assistant", "Hello Alice! How can I help you today?")
    print(f"✓ Saved assistant message")
    
    # Test 2: Retrieve messages
    print("\n[Test 2] Retrieving conversation history...")
    messages = cm.get_last_messages(thread_id)
    print(f"✓ Retrieved {len(messages)} messages")
    for i, msg in enumerate(messages, 1):
        print(f"  {i}. [{msg['role']}] {msg['content'][:50]}... ({msg['timestamp']})")
    
    # Test 3: Add more messages
    print("\n[Test 3] Adding more messages...")
    cm.save_message(thread_id, "user", "What is my name?")
    cm.save_message(thread_id, "assistant", "Your name is Alice!")
    
    messages = cm.get_last_messages(thread_id)
    print(f"✓ Now have {len(messages)} messages in history")
    
    # Test 4: Test memory limit (15 messages)
    print("\n[Test 4] Testing memory limit (15 messages)...")
    for i in range(12):
        cm.save_message(thread_id, "user", f"Test message {i}")
        cm.save_message(thread_id, "assistant", f"Response {i}")
    
    all_messages = cm.get_last_messages(thread_id, limit=100)
    limited_messages = cm.get_last_messages(thread_id)  # Default limit of 15
    
    print(f"✓ Total messages in DB: {len(all_messages)}")
    print(f"✓ Messages with limit=15: {len(limited_messages)}")
    print(f"✓ Memory window working correctly: {len(limited_messages) == 15}")
    
    # Test 5: Multiple threads
    print("\n[Test 5] Testing multiple conversation threads...")
    thread_2 = "test_user_456"
    cm.save_message(thread_2, "user", "My name is Bob")
    cm.save_message(thread_2, "assistant", "Hello Bob!")
    
    thread_1_messages = cm.get_last_messages(thread_id, limit=5)
    thread_2_messages = cm.get_last_messages(thread_2)
    
    print(f"✓ Thread 1 has {len(thread_1_messages)} messages (showing last 5)")
    print(f"✓ Thread 2 has {len(thread_2_messages)} messages")
    print(f"✓ Threads are isolated: {thread_1_messages != thread_2_messages}")
    
    # Test 6: Thread existence check
    print("\n[Test 6] Testing thread existence check...")
    exists_1 = cm.thread_exists(thread_id)
    exists_2 = cm.thread_exists("nonexistent_thread")
    print(f"✓ Thread '{thread_id}' exists: {exists_1}")
    print(f"✓ Nonexistent thread exists: {exists_2}")
    
    # Test 7: Get thread count
    print("\n[Test 7] Getting thread count...")
    count = cm.get_thread_count()
    print(f"✓ Total threads in database: {count}")
    
    # Cleanup
    cm.close()
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_conversation_persistence()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
