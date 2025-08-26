**Bing Chat Scraper**

A Selenium-based scraper that logs into Bing Chat using Microsoft credentials, bypasses basic bot detection techniques, and extracts chat responses for research or automation purposes.

⚠️ Disclaimer:
This tool is for educational and research purposes only. Automating login and scraping may violate Microsoft’s Terms of Service. Use responsibly.


---

**Features**

Automated login with Microsoft credentials

Human-like typing simulation to avoid detection

Stealth browser setup (removes navigator.webdriver, custom user agent, etc.)

CAPTCHA & verification detection (checkbox, iframe, challenge)

Optional headless mode for running without UI

Logs with UTF-8 (emoji-friendly)

Screenshot capture on errors



---

**Requirements**

Python 3.8+

Google Chrome + ChromeDriver

The following Python libraries:


pip install selenium pandas beautifulsoup4 pillow


---

**Setup**

1. Clone this repository:

git clone https://github.com/sadiakhalil125/bing-chat-scraper.git
cd bing-chat-scraper


2. Create a .env file in the project root:

BING_USERNAME="your-microsoft-account"
BING_PASSWORD="your-password"

🔒 Never commit .env with real credentials!


3. Run the scraper:

python bing_chat_scraper.py




---

**Usage**

```bash```

from bing_chat_scraper import BingChatScraper
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()
username = os.getenv("BING_USERNAME")
password = os.getenv("BING_PASSWORD")

# Create scraper instance
scraper = BingChatScraper(username, password, headless=False)

# Login
if scraper.login():
    # Send query
    response = scraper.send_query("Hello, how are you?")
    print(response)

```bash```

**Logging**

Logs are written to bing_scraper.log

Screenshots of failures are saved as .png files


**Notes**

If CAPTCHA is shown and cannot be bypassed automatically, manual intervention may be required.

Use rotating IPs or proxies if you scrape frequently.

Avoid using your primary Microsoft account.
