import asyncio
from agents import create_ray_code_agent

async def test():
    agent = create_ray_code_agent()
    # Simple test without actual data
    response = await agent.invoke_async("Create a dataset with 10 rows", session_id="test_123")
    
    print("Response type:", type(response))
    print("Response attributes:", [a for a in dir(response) if not a.startswith('_')])
    print("\nMessage:", response.message)
    print("Message content:", response.message.content if hasattr(response.message, 'content') else 'N/A')
    
    if hasattr(response.message, 'content'):
        for i, block in enumerate(response.message.content):
            print(f"\nContent block {i}:", type(block), block)

asyncio.run(test())
