
import asyncio
import yaml
from pathlib import Path
from openai import AsyncOpenAI

async def test_llm():
    print("Testing LLM connection...")
    config_path = Path("backend/config.yaml")
    if not config_path.exists():
        print("Config file not found!")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    llm_settings = config.get("llm", {}).get("main_model", {})
    base_url = llm_settings.get("base_url")
    api_key = llm_settings.get("api_key")
    model = llm_settings.get("model")

    print(f"Connecting to: {base_url}")
    print(f"Using model: {model}")

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        print("Success!")
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Failed to connect to LLM: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
