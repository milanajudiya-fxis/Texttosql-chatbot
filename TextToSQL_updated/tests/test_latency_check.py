import requests
import time
import sys

def test_latency():
    url = "http://localhost:8010/query"
    payload = {"question": "How many tables are there?"}
    
    print(f"Testing latency for {url}...")
    
    latencies = []
    
    # 5 iterations
    for i in range(5):
        start = time.time()
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            elapsed = time.time() - start
            latencies.append(elapsed)
            print(f"Request {i+1}: {elapsed:.4f}s - Status: {response.status_code}")
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
            
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"\nAverage Latency: {avg_latency:.4f}s")
        print(f"First Request: {latencies[0]:.4f}s")
        if len(latencies) > 1:
            avg_subsequent = sum(latencies[1:]) / (len(latencies) - 1)
            print(f"Subsequent Avg: {avg_subsequent:.4f}s")
    
if __name__ == "__main__":
    # Wait a bit for server to start if running immediately after startup
    time.sleep(2) 
    test_latency()
