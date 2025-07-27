import datetime
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import platform # To detect OS for ChromeDriver path

from selenium.webdriver.common.by import By


def get_chromedriver_path():
    """
    Helper function to provide a placeholder for your ChromeDriver path.
    You MUST replace this with your actual ChromeDriver path.
    """
    os_name = platform.system()
    if os_name == "Windows":
        return "C:\\path\\to\\your\\chromedriver.exe" # Example for Windows
    elif os_name == "Darwin": # macOS
        return "/path/to/your/chromedriver" # Example for macOS
    elif os_name == "Linux":
        return "/home/toby-nichol/apps/chromedriver-linux64/chromedriver" # Example for Linux
    else:
        raise OSError("Unsupported operating system for ChromeDriver path.")


def open_human_like_chrome(url_to_open="chrome://version"):
    """
    Opens Chrome with options to make it appear more human.
    """
    # Set up Chrome options
    options = Options()

    options.add_experimental_option("excludeSwitches", [
        "enable-automation",  # Removes the "controlled by automated software" infobar
        "enable-logging",     # Prevents unnecessary log messages
        "test-type",          # Often added by automation tools
        "webdriver",          # Another common indicator of automation
        # You might need to add more flags if you inspect chrome://version
        # and find other persistent automation-related flags.
        # e.g., "disable-client-side-phishing-detection" might be a default
        # Chrome flag that we might not be able to fully remove,
        # but we focus on ChromeDriver-specific ones.
    ])
    # --- Further options to make it less detectable ---
    # Disable the automation extension
    options.add_experimental_option("useAutomationExtension", False)

    # Disable infobars generally (redundant with "enable-automation" removal, but safe)
    options.add_argument("--disable-infobars")

    # Set a common User-Agent (important for appearing human-like to websites)
    # Get a recent user agent from your regular browser (search "what is my user agent")
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")

    # Maximize the window to avoid the default smaller automation window
    options.add_argument("--start-maximized")

    # Optional: Disable features that are often off in a normal user's browser
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")  # Often needed in containerized envs, but can be used here.
    options.add_argument("--disable-dev-shm-usage")  # Prevents issues in some environments.

    # If you see "remote-debugging-port" in your command line, you might need to
    # explicitly tell Selenium NOT to use it, or ChromeDriver might still add it.
    # This is a bit more advanced, as it's how Selenium communicates.
    # It's usually safe to leave it, as it's not a user-facing flag.

    # Set up ChromeDriver service
    # Replace with the actual path to your chromedriver executable
    DRIVER_PATH = get_chromedriver_path() # Uncomment and set your path
    # For demonstration, assuming chromedriver is in PATH or current dir for simplicity if not using the helper
    try:
        service = Service(executable_path=DRIVER_PATH) # <<<<< IMPORTANT: Update this line
        driver = webdriver.Chrome(service=service, options=options)

        print(f"Opening Chrome to: {url_to_open}")
        driver.get(url_to_open)

        # Keep the browser open for a few seconds to observe
        print("Browser open. Check for 'controlled by' message.")
        time.sleep(30) # Adjust as needed to inspect the browser
        print(datetime.datetime.now())
        while True:
            driver.refresh()
            page_source = driver.page_source
            if "<button class=\"add-to-cart-button--PZmQF btn--ICBoB btn-tertiary--_2uKVi disabled--vkECP\" type=\"button\" disabled=\"\">Unavailable</button>" in page_source:
                time.sleep(2)
                print("item still unavailable!!")
            else:
                print("page has changed.")
                print(datetime.datetime.now())
            if "<button class=\"add-to-cart-button--PZmQF btn--ICBoB btn-secondary--mtUol\" type=\"button\">Add to Basket</button>" in page_source:
                print("found it!")
            time.sleep(random.uniform(45, 60))



    except Exception as e:
        print(f"An error occurred: {e}")
        print("Make sure your ChromeDriver path is correct and Chrome/ChromeDriver versions match.")

if __name__ == "__main__":
    # You can test with chrome://version or any other URL
    open_human_like_chrome("https://www.pokemoncenter.com/en-gb/product/100-10617/pokemon-tcg-scarlet-and-violet-destined-rivals-booster-display-box-36-packs")
    # open_human_like_chrome("https://www.google.com")