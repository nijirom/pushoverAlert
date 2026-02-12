import requests
import time
import sys

PUSHOVER_API_TOKEN = ""
PUSHOVER_USER_KEY = ""
TARGET_LEVEL = 
SYMBOL = ""
CHECK_INTERVAL_SECONDS = 5

TICKER_API_URL = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"

CRITICAL_BACKOFF_SECONDS = 1800 

ALERT_SENT = False

def send_pushover_notification(title, message, priority=+2):
    if PUSHOVER_API_TOKEN == "" or \
       PUSHOVER_USER_KEY == "":
        print("API not configured")
        return False

    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
        "priority": priority,
    }

    try:
        response = requests.post(PUSHOVER_URL, data=payload, timeout=10)
        response.raise_for_status()
        
        if response.json().get('status') == 1:
            print(f"Pushover notification sent. Title: {title}")
            return True
        else:
            print(f"Pushover API Error: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request Error when sending Pushover notification: {e}")
        return False


def get_ethbtc_price():
    try:
        response = requests.get(TICKER_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = float(data.get('price'))
        return price, CHECK_INTERVAL_SECONDS
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 451:
            error_message = f"CRITICAL ERROR: Binance returned 451 Client Error (Rate Limit Ban). Backing off for {CRITICAL_BACKOFF_SECONDS} seconds."
            print(error_message)
            send_pushover_notification("Monitor Paused (Binance 451)", error_message, priority=-1) 
            return None, CRITICAL_BACKOFF_SECONDS
        
        print(f"Error fetching price from Binance API: {e}")
        return None, CHECK_INTERVAL_SECONDS
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price from Binance API: {e}")
        return None, CHECK_INTERVAL_SECONDS
    
    except (ValueError, TypeError, KeyError) as e:
        print(f"Error parsing price data: {e}. API response was: {response.text}")
        return None, CHECK_INTERVAL_SECONDS


def main():
    global ALERT_SENT
    print(f"--- Starting {SYMBOL} Price Monitor ---")
    print(f"Target Level: {TARGET_LEVEL}")

    while True:
        current_price, wait_time = get_ethbtc_price()

        if current_price is None:
            print(f"Price retrieval failed. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        print(f"Current Price ({SYMBOL}): {current_price:.6f}")

        if current_price >= TARGET_LEVEL:
            if not ALERT_SENT:
                title = f"{SYMBOL} LEVEL BREACHED!"
                message = f"{SYMBOL} ratio is now {current_price:.6f} (>= {TARGET_LEVEL})."
                
                if send_pushover_notification(title, message):
                    ALERT_SENT = True
            else:
                print("Waiting")
        else:
            if ALERT_SENT:
                print("Price below target. Resetting")
                ALERT_SENT = False

            print("Waiting")
        
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
    except Exception as e:
        print(f"An unhandled error occurred: {e}")

        sys.exit(1)

