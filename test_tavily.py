import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    print("ERROR: API key not found in .env")
else:
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "query": "benefits of online education",
                "search_depth": "basic",
                "max_results": 3
            },
            timeout=20
        )

        print("HTTP STATUS:", response.status_code)

        if response.ok:
            results = response.json().get("results", [])

            print("SUCCESS: Tavily connected")
            print("RESULTS FOUND:", len(results))

            for item in results:
                print("SOURCE:", item.get("url"))
        else:
            print("API ERROR:", response.status_code)
            print(response.text[:200])

    except requests.RequestException as error:
        print("CONNECTION ERROR:", type(error).__name__)