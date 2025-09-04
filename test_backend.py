#!/usr/bin/env python3
"""
Simple test script to verify backend functionality
"""
import asyncio
import aiohttp
import json

async def test_backend():
    """Test backend endpoints"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("Testing health endpoint...")
        async with session.get(f"{base_url}/api/health") as resp:
            print(f"Health status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Health response: {data}")
            else:
                print("Health check failed!")
                return
        
        # Test root endpoint
        print("\nTesting root endpoint...")
        async with session.get(f"{base_url}/") as resp:
            print(f"Root status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Root response: {data}")
        
        print("\n✅ Backend is running successfully!")
        print("You can now test the full application by:")
        print("1. Starting the frontend with: cd frontend && npm run dev")
        print("2. Opening http://localhost:5173 in your browser")

if __name__ == "__main__":
    try:
        asyncio.run(test_backend())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nMake sure the backend is running:")
        print("Run: start-backend.bat")