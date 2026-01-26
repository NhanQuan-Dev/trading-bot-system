import asyncio
import os
import sys
import subprocess

BACKTEST_ID = "74a222c5-6d5b-4f83-b801-aa5964bcf794"
URL = f"http://localhost:8000/api/v1/backtests/{BACKTEST_ID}/trades?page=1&limit=5"

def main():
    print(f"Curling: {URL}")
    try:
        # Use simple curl command
        result = subprocess.run(["curl", "-s", URL], capture_output=True, text=True)
        if result.returncode == 0:
            print("Response:")
            print(result.stdout)
        else:
            print(f"Error: {result.stderr}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
