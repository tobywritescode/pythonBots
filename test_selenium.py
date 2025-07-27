from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# --- IMPORTANT: Replace with the actual path to your chromedriver executable ---
# If chromedriver is in your system's PATH, you might not need the executable_path argument.
# Otherwise, provide the full path:
# DRIVER_PATH = "/path/to/your/chromedriver"
# For example, on Windows: DRIVER_PATH = "C:\\Users\\YourUser\\Downloads\\chromedriver-win64\\chromedriver.exe"
# For example, on macOS/Linux: DRIVER_PATH = "/Users/YourUser/Downloads/chromedriver"
DRIVER_PATH = "/home/toby-nichol/apps/chromedriver-linux64/chromedriver.exe" # Replace with your actual path

def open_chrome_and_navigate(url_to_open = "google.com"):
    """
    Opens Chrome, navigates to a URL by typing into the address bar,
    and then waits briefly before closing the browser.
    """
    try:
        # Initialize the Chrome WebDriver
        # If chromedriver is in your PATH, you can just do:
        # driver = webdriver.Chrome()
        driver = webdriver.Chrome()

        print(f"Opening Chrome and navigating to: {url_to_open}")

        # Navigate to a dummy page first (e.g., Google) to ensure a clean address bar.
        # This gives us a known starting point to manipulate the address bar.
        driver.get("https://www.google.com")
        time.sleep(1) # Give the page a moment to load

        # To "insert text into the address bar" and navigate,
        # we can't directly interact with the browser's native address bar for security reasons.
        # Instead, we'll simulate opening a new tab or directly navigating.
        # The most straightforward way is to use driver.get() directly with the target URL.
        # However, if you *insist* on typing into an address bar *like* element,
        # you'd need to find a search bar on a page (like Google's) and type there,
        # then press enter, which effectively navigates.

        # Option 1: Direct navigation (most common and recommended)
        # This is the most reliable way to go to a URL.
        print(f"Navigating directly to: {url_to_open}")
        driver.get(url_to_open)
        time.sleep(3500000) # Keep the browser open for 3 seconds so you can see it

        # Option 2 (If you specifically want to type into a search bar-like element and press enter):
        # This simulates typing into a search engine's search bar, which then navigates.
        # This isn't "the address bar" but a common way to achieve navigation by text input.
        # For this to work, you'd need to be on a page with a search bar (e.g., google.com).
        # Uncomment the following block if this is your desired behavior.
        # driver.get("https://www.google.com")
        # time.sleep(1)
        # search_box = driver.find_element(By.NAME, "q") # 'q' is the name attribute for Google's search box
        # search_box.send_keys(url_to_open)
        # search_box.send_keys(Keys.RETURN) # Simulate pressing Enter
        # time.sleep(3) # Wait for the search results to load or redirection to happen


    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the browser
        if 'driver' in locals() and driver:
            driver.quit()
            print("Browser closed.")

# --- Example Usage ---
if __name__ == "__main__":
    target_url = "https://www.pokemoncenter.com/en-gb/category/destined-rivals"
    open_chrome_and_navigate(target_url)