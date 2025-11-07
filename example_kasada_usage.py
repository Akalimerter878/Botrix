"""
Example usage of KasadaSolver module

This file demonstrates how to use the KasadaSolver class
to bypass Kasada protection on Kick.com
"""

import asyncio
import os
from dotenv import load_dotenv
from workers.kasada_solver import KasadaSolver, KasadaSolverError

# Load environment variables
load_dotenv()


async def example_basic_usage():
    """Basic usage example"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Initialize solver with API key from environment
    solver = KasadaSolver(api_key=os.getenv("RAPIDAPI_KEY"), test_mode=True)
    
    try:
        # Solve Kasada challenge for Kick.com signup endpoint
        headers = await solver.solve(
            method="POST",
            fetch_url="https://kick.com/api/v1/signup/send/email"
        )
        
        print("\n✅ Successfully obtained Kasada headers:")
        for key, value in headers.items():
            print(f"  {key}: {value[:50]}..." if len(value) > 50 else f"  {key}: {value}")
        
    except KasadaSolverError as e:
        print(f"\n❌ Error: {e}")
    
    finally:
        await solver.close()
        print("\n✅ Solver closed\n")


async def example_context_manager():
    """Using async context manager"""
    print("=" * 60)
    print("Example 2: Using Async Context Manager")
    print("=" * 60)
    
    # Using context manager (automatically closes)
    async with KasadaSolver(api_key=os.getenv("RAPIDAPI_KEY"), test_mode=True) as solver:
        headers = await solver.solve(
            method="POST",
            fetch_url="https://kick.com/api/v1/signup/send/email"
        )
        
        print("\n✅ Headers obtained via context manager:")
        print(f"  Found {len(headers)} headers")
    
    print("✅ Context manager automatically closed the solver\n")


async def example_error_handling():
    """Error handling example"""
    print("=" * 60)
    print("Example 3: Error Handling")
    print("=" * 60)
    
    solver = KasadaSolver(api_key="invalid_key", test_mode=True)
    
    try:
        # This will fail due to missing URL
        await solver.solve(method="POST", fetch_url="")
    except ValueError as e:
        print(f"\n✅ Caught ValueError as expected: {e}")
    
    await solver.close()
    print()


async def example_multiple_requests():
    """Making multiple requests with rate limiting"""
    print("=" * 60)
    print("Example 4: Multiple Requests (Rate Limited)")
    print("=" * 60)
    
    async with KasadaSolver(api_key=os.getenv("RAPIDAPI_KEY"), test_mode=True) as solver:
        endpoints = [
            "https://kick.com/api/v1/signup/send/email",
            "https://kick.com/api/v1/verify",
            "https://kick.com/api/v1/complete"
        ]
        
        print("\nMaking 3 requests (notice 1 second delay between each):\n")
        
        for i, endpoint in enumerate(endpoints, 1):
            print(f"Request {i}: {endpoint}")
            headers = await solver.solve(method="POST", fetch_url=endpoint)
            print(f"  ✅ Received {len(headers)} headers\n")


async def example_live_api():
    """Example using live API (requires valid API key)"""
    print("=" * 60)
    print("Example 5: Live API Call (Requires Valid API Key)")
    print("=" * 60)
    
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key or api_key == "your_key_here":
        print("\n⚠️  Skipped: Please set RAPIDAPI_KEY in .env file")
        print("   This example requires a valid RapidAPI key\n")
        return
    
    # Set test_mode=False to make real API calls
    async with KasadaSolver(api_key=api_key, test_mode=False) as solver:
        try:
            headers = await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/v1/signup/send/email"
            )
            
            print("\n✅ Live API call successful!")
            print(f"  Received {len(headers)} headers from actual Kasada API")
            
        except KasadaSolverError as e:
            print(f"\n❌ Live API call failed: {e}")
            print("   Check your API key and account status")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print(" Kasada Solver - Usage Examples")
    print("=" * 60 + "\n")
    
    await example_basic_usage()
    await example_context_manager()
    await example_error_handling()
    await example_multiple_requests()
    await example_live_api()
    
    print("=" * 60)
    print(" All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
