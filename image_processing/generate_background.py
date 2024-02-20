import requests
from dotenv import load_dotenv
import os

load_dotenv()


def generate_image(prompt):
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(os.getenv("OPEN_AI_KEY")),
    }
    payload = {"prompt": prompt, "n": 1, "size": "1024x1024"}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        # Assuming the API response contains an image URL. Adjust the key based on actual API response structure
        image_url = data["data"][0][
            "url"
        ]  # Adjust this line based on the actual structure of the response
        return image_url
    else:
        print(f"Error: {response.status_code}")

        return None
