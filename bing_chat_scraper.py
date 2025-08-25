import time
import json
import logging
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
import random
import re
from bs4 import BeautifulSoup
import sqlite3
import os
import base64
from PIL import Image
import io

# Set up logging with UTF-8 encoding to handle emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bing_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Set console to handle UTF-8 for Windows
import sys
if sys.platform.startswith('win'):
    import os
    os.system('chcp 65001 >nul 2>&1')  # Set Windows console to UTF-8

class BingChatScraper:
    def __init__(self, username, password, headless=False, verification_timeout=30):
        self.username = username
        self.password = password
        self.headless = headless
        self.verification_timeout = verification_timeout
        self.driver = None
        self.wait = None
        self.setup_driver()
        
    def setup_driver(self):
        """Set up Chrome driver with appropriate options to mimic human behavior"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")  # New headless mode is less detectable
        chrome_options.add_argument("--no-sandbox") # Disable the sandbox. This is often required for the browser to run in a Docker container or on a Linux server
        chrome_options.add_argument("--disable-dev-shm-usage") # Overcomes resource limitations in some environments by preventing crashes related to shared memory.
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--lang=en-US,en;q=0.9")
        
        self.driver = webdriver.Chrome(options=chrome_options)
         # --- APPLY ADVANCED STEALTH TECHNIQUES AFTER LAUNCH ---
    
        # Execute a JavaScript command on the browser.
        # This script modifies the 'navigator' object to hide the 'webdriver' property,
        # which is a dead giveaway that the browser is automated. It makes it return 'undefined' instead of 'true'.
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.wait = WebDriverWait(self.driver, 20)
        
    def check_for_human_verification(self):
        """Check if human verification is required and handle it"""
        """
        (Role: DETECTOR)
        Quickly scans the page for any signs of a human verification challenge.
        This method is non-interactive; it only looks, it doesn't touch.
        """
        try:
            # Look for various verification elements
            verification_selectors = [
                "input[type='checkbox']",
                "#verify-human",
                ".verification-checkbox",
                "[aria-label*='verify']",
                "[data-testid*='verification']",
                "[id*='captcha']",
                "[class*='captcha']",
                "iframe[title*='recaptcha']"
            ]
            
            for selector in verification_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        # Check if it's a verification checkbox
                        if self.is_verification_element(element):
                            logging.warning("Human verification required")
                            return True
                except:
                    continue
            
            # Check for iframes that might contain verification
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    src = iframe.get_attribute("src") or ""
                    if any(term in src for term in ['captcha', 'verify', 'challenge']):
                        logging.warning("Verification iframe detected")
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            logging.error(f"Error checking for verification: {str(e)}")
            return False
    
    def is_verification_element(self, element):
        """Check if an element is a verification element"""
        """
        (Role: CONFIRMER - A helper function)
        Inspects a single, specific web element to determine if it is part of a verification challenge.
        It does this by checking multiple HTML attributes for a list of known keywords.
        """
        try:
            # Check various attributes that might indicate verification
            attrs_to_check = [
                element.get_attribute("id"),
                element.get_attribute("class"),
                element.get_attribute("name"),
                element.get_attribute("aria-label"),
                element.get_attribute("data-testid")
            ]
            
            verification_indicators = [
                'verify', 'human', 'robot', 'captcha', 'challenge', 
                'verification', 'checkbox', 'notrobot'
            ]
            
            for attr in attrs_to_check:
                if attr and any(indicator in attr.lower() for indicator in verification_indicators):
                    return True
                    
            return False
            
        except:
            return False
    
    def handle_human_verification(self):
        """Handle human verification if required"""
        """
        (Role: ACTOR)
        Attempts to solve a human verification challenge, specifically simple ones like checkboxes.
        This method is interactive: it scrolls, clicks, and waits.
        """
        start_time = time.time()
        
        while time.time() - start_time < self.verification_timeout:
            try:
                # Look for verification elements
                verification_selectors = [
                    "input[type='checkbox']",
                    "#verify-human",
                    ".verification-checkbox",
                    "[aria-label*='verify']",
                    "[data-testid*='verification']"
                ]
                
                for selector in verification_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if self.is_verification_element(element) and element.is_displayed():
                                logging.info("Found verification checkbox, attempting to click")
                                
                                # Scroll to the element
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                time.sleep(1)
                                
                                # Try to click the element
                                try:
                                    element.click()
                                    logging.info("Clicked verification checkbox")
                                    time.sleep(3)
                                    return True
                                except (ElementNotInteractableException, ElementClickInterceptedException):
                                    # Try JavaScript click as fallback
                                    self.driver.execute_script("arguments[0].click();", element)
                                    logging.info("Used JavaScript to click verification checkbox")
                                    time.sleep(3)
                                    return True
                    except:
                        continue
                
                # Check for CAPTCHA iframes
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        src = iframe.get_attribute("src") or ""
                        if any(term in src for term in ['captcha', 'verify']):
                            logging.warning("CAPTCHA verification detected. Manual intervention may be required.")
                            # Take screenshot for debugging
                            self.driver.save_screenshot("captcha_verification.png")
                            return False
                    except:
                        continue
                
                time.sleep(2)
                
            except Exception as e:
                logging.error(f"Error handling verification: {str(e)}")
                time.sleep(2)
        
        logging.error("Verification handling timeout")
        return False
    
    def login(self):
        """Log in to Bing Chat with provided credentials"""
        try:
            logging.info("Navigating to Bing Chat...")
            self.driver.get("https://www.bing.com/chat")
            time.sleep(3)
            
            # Check for human verification before proceeding
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Failed to complete human verification")
                    return False
            
            # Check if already logged in
            current_url = self.driver.current_url.lower()
            if "login" not in current_url and "signin" not in current_url:
                logging.info("Already logged in or on chat page")
                return True
                
            # Wait for and click the sign-in button
            logging.info("Looking for sign-in button...")
            try:
                sign_in_button = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "id_a"))
                )
                sign_in_button.click()
            except:
                # Try alternative selectors for sign-in button
                sign_in_selectors = [
                    "a[class*='signin']",
                    "button[class*='signin']",
                    "a[href*='login']",
                    "button:contains('Sign in')",
                    "a:contains('Sign in')"
                ]
                
                for selector in sign_in_selectors:
                    try:
                        sign_in_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        sign_in_button.click()
                        break
                    except:
                        continue
            
            # Check for human verification after clicking sign-in
            time.sleep(2)
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Failed to complete human verification after sign-in")
                    return False
            
            # Wait for login form and enter credentials
            logging.info("Waiting for login form...")
            username_field = self.wait.until(
                EC.visibility_of_element_located((By.NAME, "loginfmt"))
            )
            
            # Type username slowly to mimic human behavior
            self.human_type(username_field, self.username)
            username_field.send_keys(Keys.RETURN)
            
            # Check for human verification after entering username
            time.sleep(2)
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Failed to complete human verification after username")
                    return False
            
            # Wait for password field
            password_field = self.wait.until(
                EC.visibility_of_element_located((By.NAME, "passwd"))
            )
            
            # Type password slowly
            self.human_type(password_field, self.password)
            password_field.send_keys(Keys.RETURN)
            
            # Check for human verification after entering password
            time.sleep(2)
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Failed to complete human verification after password")
                    return False
            
            # Handle "Stay signed in" prompt if it appears
            time.sleep(2)
            try:
                no_button = self.driver.find_element(By.ID, "idBtn_Back")
                no_button.click()
            except NoSuchElementException:
                pass
                
            # Final verification check
            time.sleep(3)
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Failed to complete final human verification")
                    return False
                
            # Wait for chat interface to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, input[type='text'], [contenteditable='true']"))
                )
            except TimeoutException:
                logging.warning("Chat interface not found, but continuing anyway")
            
            logging.info("Login successful!")
            return True
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            # Take screenshot for debugging
            self.driver.save_screenshot("login_error.png")
            return False
    
    def human_type(self, element, text):
        """Type text in a human-like manner with random delays"""
        for character in text:
            element.send_keys(character)
            time.sleep(random.uniform(0.05, 0.3))  # Random typing speed
    
    def find_input_element(self):
        """Find the chat input element using multiple strategies"""
        input_selectors = [
            "textarea[placeholder*='Ask me anything']",
            "textarea[aria-label*='Ask me anything']",
            "textarea[data-id='userInput']",
            "textarea[class*='input']",
            "input[type='text'][placeholder*='Ask']",
            "[contenteditable='true']",
            "textarea",
            "input[type='text']"
        ]
        
        for selector in input_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Additional check to make sure element is interactable
                        try:
                            # Try to scroll to element and check if it's clickable
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(1)
                            
                            # Test if element can receive focus
                            element.click()
                            time.sleep(0.5)
                            
                            logging.info(f"Found input element using selector: {selector}")
                            return element
                        except:
                            continue
            except:
                continue
        
        return None
    
    def send_query(self, query):
        """Send a query to Bing Chat and wait for response"""
        try:
            logging.info(f"Sending query: {query}")
            
            # Check for human verification before sending query
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Verification required before sending query")
                    return None
            
            # Wait a bit for any dynamic content to load
            time.sleep(3)
            
            # Get the count of existing messages before sending
            initial_message_count = self.get_message_count()
            
            # Find the chat input element with retries
            chat_input = None
            for attempt in range(3):
                chat_input = self.find_input_element()
                if chat_input:
                    break
                logging.warning(f"Input element not found, attempt {attempt + 1}/3")
                time.sleep(2)
                
            if not chat_input:
                raise Exception("Could not find chat input element after multiple attempts")
            
            # Wait for element to be fully interactive
            time.sleep(1)
            
            # Clear any existing text
            try:
                chat_input.clear()
            except:
                # Try alternative clearing methods
                chat_input.send_keys(Keys.CONTROL + "a")
                chat_input.send_keys(Keys.DELETE)
            
            # Type the query in a human-like manner
            self.human_type(chat_input, query)
            time.sleep(1)
            
            # Send the query - try multiple methods
            query_sent = False
            
            # Method 1: Enter key
            try:
                chat_input.send_keys(Keys.RETURN)
                query_sent = True
                logging.info("Query sent using Enter key")
            except:
                logging.warning("Enter key failed, trying send button")
            
            # Method 2: Send button if Enter failed
            if not query_sent:
                send_button_selectors = [
                    "button[aria-label*='Send']",
                    "button[title*='Send']",
                    "button[data-testid*='send']",
                    "button svg[data-icon='send']",
                    "[role='button'][aria-label*='Send']"
                ]
                
                for selector in send_button_selectors:
                    try:
                        send_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if send_button.is_displayed() and send_button.is_enabled():
                            send_button.click()
                            query_sent = True
                            logging.info("Query sent using send button")
                            break
                    except:
                        continue
            
            if not query_sent:
                raise Exception("Failed to send query using any method")
            
            # Wait for new message to appear (indicating query was sent successfully)
            message_appeared = self.wait_for_new_message(initial_message_count, timeout=15)
            
            if not message_appeared:
                logging.warning("New message did not appear, but continuing...")
            else:
                logging.info("Query sent, waiting for response...")
            
            # Check for human verification after sending query
            time.sleep(2)
            if self.check_for_human_verification():
                if not self.handle_human_verification():
                    logging.error("Verification required after sending query")
                    return None
            
            # Wait for response to complete
            response_complete = self.wait_for_response_completion()
            
            if not response_complete:
                logging.warning("Response may not be complete, but continuing...")
            
            # Check for human verification after response
            if self.check_for_human_verification():
                logging.warning("Verification required after response")
                # Continue anyway to extract the response
            
            # Extract the response
            response = self.extract_response()
            
            if response and response.get('text'):
                logging.info(f"Response received: {len(response['text'])} characters")
            else:
                logging.warning("No response text found")
            
            return response
            
        except Exception as e:
            logging.error(f"Error sending query: {str(e)}")
            # Take screenshot for debugging
            self.driver.save_screenshot(f"query_error_{int(time.time())}.png")
            return None
    
    def get_message_count(self):
        """Get the current count of messages in the chat"""
        try:
            # Look for user messages
            user_messages = self.driver.find_elements(By.CSS_SELECTOR, "[data-content='user-message']")
            # Look for AI response messages
            ai_messages = self.driver.find_elements(By.CSS_SELECTOR, ".group\\/ai-message-item")
            
            return len(user_messages) + len(ai_messages)
        except:
            return 0
    
    def wait_for_new_message(self, initial_count, timeout=10):
        """Wait for a new message to appear in the chat"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_count = self.get_message_count()
                if current_count > initial_count:
                    return True
                time.sleep(1)
            except:
                time.sleep(1)
                continue
        
        logging.warning("Timeout waiting for new message to appear")
        return False
    
    def wait_for_response_completion(self, timeout=120):
        """Wait for the AI response to be fully generated"""
        start_time = time.time()
        last_change = time.time()
        last_text = ""
        stable_count = 0
        
        logging.info("Waiting for response to complete...")
        
        while time.time() - start_time < timeout:
            try:
                # Check for typing indicators
                typing_indicators = self.driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='typing'], [class*='loading'], [class*='generating'], .animate-pulse")
                
                if typing_indicators:
                    # Reset stable count if typing indicators are present
                    stable_count = 0
                    time.sleep(2)
                    continue
                
                # Get current response text from the latest AI message
                ai_messages = self.driver.find_elements(By.CSS_SELECTOR, ".group\\/ai-message-item")
                
                if not ai_messages:
                    time.sleep(2)
                    continue
                
                # Get the latest AI message
                latest_message = ai_messages[-1]
                
                # Get text from p tags within the message
                p_tags = latest_message.find_elements(By.TAG_NAME, "p")
                current_text = " ".join([p.text for p in p_tags if p.text.strip()])
                
                # Check if text has changed
                if current_text != last_text and current_text.strip():
                    last_text = current_text
                    last_change = time.time()
                    stable_count = 0
                    logging.debug(f"Response text updated, length: {len(current_text)}")
                else:
                    stable_count += 1
                
                # If text hasn't changed for multiple checks, consider it complete
                if stable_count >= 5 and current_text.strip():
                    logging.info("Response appears to be complete")
                    return True
                
                time.sleep(2)
                
            except StaleElementReferenceException:
                # Element became stale, continue to refresh our reference
                time.sleep(2)
                continue
            except Exception as e:
                logging.warning(f"Error waiting for response: {str(e)}")
                time.sleep(2)
                continue
        
        logging.warning("Response timeout reached, but may still have partial response")
        return False
    
    def extract_response(self):
        """Extract the response text from the latest AI message"""
        try:
            # Find all AI message elements
            ai_messages = self.driver.find_elements(By.CSS_SELECTOR, ".group\\/ai-message-item")
            
            if not ai_messages:
                logging.warning("No AI messages found")
                return None
                
            # Get the latest AI message
            latest_message = ai_messages[-1]
            
            # Extract text from p tags within the message
            p_tags = latest_message.find_elements(By.TAG_NAME, "p")
            response_text = ""
            
            for p in p_tags:
                text = p.text.strip()
                if text:
                    response_text += text + "\n"
            
            # Clean up the text
            response_text = response_text.strip()
            
            if not response_text:
                # Fallback: try to get all text from the message element
                response_text = latest_message.text.strip()
            
            # Extract any citations/links
            citations = []
            try:
                links = latest_message.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href and 'http' in href:
                        citations.append(href)
            except:
                pass
            
            # Get the HTML for debugging/storage
            response_html = ""
            try:
                response_html = latest_message.get_attribute('outerHTML')
            except:
                pass
            
            if not response_text:
                logging.warning("No response text extracted")
                return None
            
            return {
                'text': response_text,
                'citations': citations,
                'html': response_html,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error extracting response: {str(e)}")
            return None
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


class DataProcessor:
    """Class for processing and storing scraped data"""
    
    def __init__(self, db_path='bing_chat_data.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table for chat interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                response_text TEXT,
                citations TEXT,
                response_html TEXT,
                timestamp DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create table for analysis results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT,
                result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create table for tracking verification events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                timestamp DATETIME,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_interaction(self, query, response):
        """Store a query-response interaction in the database"""
        if not response:
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO interactions (query, response_text, citations, response_html, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                query, 
                response['text'], 
                json.dumps(response['citations']), 
                response['html'],
                response['timestamp']
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error storing interaction: {str(e)}")
            return False
    
    def record_verification_event(self, event_type, details=None):
        """Record a verification event"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO verification_events (event_type, timestamp, details)
                VALUES (?, ?, ?)
            ''', (event_type, datetime.now().isoformat(), details))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Error recording verification event: {str(e)}")
            return False
    
    def load_interactions(self, limit=100):
        """Load interactions from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, query, response_text, citations, timestamp 
                FROM interactions 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            interactions = []
            for row in rows:
                interactions.append({
                    'id': row[0],
                    'query': row[1],
                    'response_text': row[2],
                    'citations': json.loads(row[3]) if row[3] else [],
                    'timestamp': row[4]
                })
                
            return interactions
            
        except Exception as e:
            logging.error(f"Error loading interactions: {str(e)}")
            return []
    
    def analyze_response_length(self):
        """Analyze response length statistics"""
        interactions = self.load_interactions(limit=1000)
        
        if not interactions:
            return None
            
        response_lengths = [len(interaction['response_text']) for interaction in interactions]
        
        analysis = {
            'total_interactions': len(interactions),
            'avg_response_length': sum(response_lengths) / len(response_lengths),
            'min_response_length': min(response_lengths),
            'max_response_length': max(response_lengths),
            'response_lengths': response_lengths
        }
        
        # Store analysis result
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analysis_results (analysis_type, result)
                VALUES (?, ?)
            ''', ('response_length', json.dumps(analysis)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error storing analysis: {str(e)}")
            
        return analysis
    
    def analyze_citation_patterns(self):
        """Analyze citation patterns in responses"""
        interactions = self.load_interactions(limit=1000)
        
        if not interactions:
            return None
            
        citation_counts = [len(interaction['citations']) for interaction in interactions]
        has_citations = sum(1 for count in citation_counts if count > 0)
        
        analysis = {
            'total_interactions': len(interactions),
            'interactions_with_citations': has_citations,
            'percent_with_citations': (has_citations / len(interactions)) * 100 if interactions else 0,
            'avg_citations': sum(citation_counts) / len(citation_counts) if interactions else 0,
            'max_citations': max(citation_counts) if interactions else 0,
            'citation_counts': citation_counts
        }
        
        # Store analysis result
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analysis_results (analysis_type, result)
                VALUES (?, ?)
            ''', ('citation_patterns', json.dumps(analysis)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error storing analysis: {str(e)}")
            
        return analysis
    
    def export_to_csv(self, filename='bing_chat_data.csv'):
        """Export interactions to CSV file"""
        interactions = self.load_interactions()
        
        if not interactions:
            return False
            
        df = pd.DataFrame(interactions)
        df.to_csv(filename, index=False)
        return True


def main():
    # Configuration

    USERNAME = os.getenv("BING_USERNAME") 
    PASSWORD = os.getenv("BING_PASSWORD")             
    QUERIES = [
        "Hello!", #first query to start verification checkbox (will produce no response)
        "What is the capital of France?",
        "Explain the theory of relativity in simple terms",
        "What are the benefits of renewable energy?",
    ]
    
    # Initialize scraper and data processor
    scraper = BingChatScraper(USERNAME, PASSWORD, headless=False)
    processor = DataProcessor()
    
    try:
        # Login to Bing Chat
        if not scraper.login():
            logging.error("Failed to login. Exiting.")
            return
        
        logging.info("Login successful, starting query processing...")
        
        # Wait extra time after login to handle any verification or page loading
        logging.info("Waiting 3 seconds for page to fully load and handle any verification...")
        time.sleep(3)
        
        # Check for and handle any remaining verification
        if scraper.check_for_human_verification():
            logging.info("Handling post-login verification...")
            scraper.handle_human_verification()
            time.sleep(120)  # Additional wait after verification
        
        # Send queries with random delays to avoid detection
        successful_queries = 0
        for i, query in enumerate(QUERIES):
            logging.info(f"Processing query {i+1}/{len(QUERIES)}: {query}")
            
            try:
                # Random delay between requests (between 15 and 35 seconds)
                if i > 0:  # Skip delay for first query after login wait
                    delay = random.uniform(15, 35)
                    logging.info(f"Waiting for {delay:.2f} seconds before sending query...")
                    time.sleep(delay)
                
                # Send query and get response
                response = scraper.send_query(query)
                
                if response and response.get('text'):
                    # Store the interaction
                    if processor.store_interaction(query, response):
                        successful_queries += 1
                        logging.info(f"[SUCCESS] Query {i+1} successful - Response length: {len(response['text'])} characters")
                        
                        # Print first 200 characters of response for verification
                        preview = response['text'][:200] + "..." if len(response['text']) > 200 else response['text']
                        logging.info(f"Response preview: {preview}")
                    else:
                        logging.error(f"[ERROR] Failed to store interaction for query {i+1}")
                else:
                    logging.warning(f"[WARNING] No response received for query {i+1}: {query}")
                
                # Additional random delay after processing
                time.sleep(random.uniform(3, 8))
                
            except Exception as e:
                logging.error(f"[ERROR] Error processing query {i+1}: {str(e)}")
                # Take screenshot for debugging
                scraper.driver.save_screenshot(f"query_{i+1}_error_{int(time.time())}.png")
                continue
        
        logging.info(f"Query processing completed. Successful queries: {successful_queries}/{len(QUERIES)}")
        
        if successful_queries > 0:
            # Perform data analysis
            logging.info("Performing data analysis...")
            
            # Analyze response lengths
            length_analysis = processor.analyze_response_length()
            if length_analysis:
                logging.info(f"[ANALYSIS] Response length analysis:")
                logging.info(f"  - Total interactions: {length_analysis['total_interactions']}")
                logging.info(f"  - Average response length: {length_analysis['avg_response_length']:.1f} characters")
                logging.info(f"  - Min length: {length_analysis['min_response_length']}")
                logging.info(f"  - Max length: {length_analysis['max_response_length']}")
            
            # Analyze citation patterns
            citation_analysis = processor.analyze_citation_patterns()
            if citation_analysis:
                logging.info(f"[ANALYSIS] Citation analysis:")
                logging.info(f"  - Interactions with citations: {citation_analysis['interactions_with_citations']}")
                logging.info(f"  - Percentage with citations: {citation_analysis['percent_with_citations']:.1f}%")
                logging.info(f"  - Average citations per response: {citation_analysis['avg_citations']:.1f}")
            
            # Export data to CSV
            if processor.export_to_csv():
                logging.info("[SUCCESS] Data exported to CSV successfully")
            
            logging.info("[COMPLETE] Scraping and analysis completed successfully!")
        else:
            logging.error("[ERROR] No successful queries processed")
        
    except KeyboardInterrupt:
        logging.info("Script interrupted by user")
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {str(e)}")
        # Take screenshot for debugging
        try:
            scraper.driver.save_screenshot(f"main_error_{int(time.time())}.png")
        except:
            pass
    
    finally:
        # Close the browser
        try:
            scraper.close()
            logging.info("Browser closed")
        except:
            pass


if __name__ == "__main__":
    main()