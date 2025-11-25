import requests
import time
import os

# Read bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN", "7581428285:AAF6qwxQYniDoZnhiwERUP_k0Vlf-k6MVSQ")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
# For production, use your Render URL. For local dev, use localhost
# Default to production URL if FLASK_URL env var is not set
FLASK_URL = os.getenv("FLASK_URL", "https://stockboy.works/telegram-update")

def main():
    last_update_id = None


    while True:
        try:
            # get updates safely
            response = requests.get(
                f"{API_URL}/getUpdates",
                params={"offset": last_update_id, "timeout": 10}
            ).json()

            # no updates found
            if "result" not in response:
                time.sleep(1)
                continue

            for update in response["result"]:

                # update pointer (VERY important to stop duplicates)
                last_update_id = update["update_id"] + 1

                # Only send CALLBACK events
                if "callback_query" in update:
                    print("Forwarding callback → Flask...")
                    requests.post(FLASK_URL, json=update)

        except Exception as e:
            print("Listener Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
