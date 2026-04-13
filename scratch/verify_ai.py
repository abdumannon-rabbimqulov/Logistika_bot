import asyncio
import os
import sys

# Add project root to sys.path
project_root = "/Users/user/Logistika_bot"
sys.path.append(project_root)

# Mock environment variables if needed
os.environ["DB_URL"] = "postgresql+asyncpg://user:pass@localhost/dbname" # This is just a placeholder, the actual .env should be loaded

from handlers.ai_agent import agent

async def test_ai():
    print("--- Testing Logistika AI Agent ---")
    
    # Test case 1: Get Profile
    print("\nCase 1: 'Mening profilimni ko'rsat'")
    res1 = await agent.process_text(user_id=123, text="Mening profilimni ko'rsat")
    print(f"Response: {res1}")

    # Test case 2: Create Order
    print("\nCase 2: 'Toshkentdan Samarqandga 3 tonna meva yubormoqchiman, narxi 400000'")
    res2 = await agent.process_text(user_id=123, text="Toshkentdan Samarqandga 3 tonna meva yubormoqchiman, narxi 400000")
    print(f"Response: {res2}")

if __name__ == "__main__":
    # We won't actually run it because DB connection will fail without real DB, 
    # but the logic is there.
    print("Verification script created. Run this in an environment with real DB and API keys.")
