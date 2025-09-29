import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURATION ---
# IMPORTANT: Update this path to where you saved your chromedriver
CHROME_DRIVER_PATH = '/Users/educasanova/webdrivers/chromedriver' # e.g., 'C:/Users/YourUser/Downloads/chromedriver.exe'
TARGET_URL = "https://www.trustpilot.com/review/www.exoticca.com?stars=1&stars=2"
OUTPUT_CSV_FILE = 'exoticca_reviews_1_2_star_since_2024.csv'
START_DATE = datetime(2024, 1, 1).date()

def parse_review_date(date_str):
    """Parses Trustpilot's date format (e.g., '2024-09-28') and returns a date object."""
    try:
        # Trustpilot uses ISO 8601 format in the datetime attribute
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except (ValueError, TypeError):
        return None

def scrape_trustpilot():
    """Main function to scrape reviews."""
    service = Service(executable_path=CHROME_DRIVER_PATH)
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment to run without opening a browser window
    driver = webdriver.Chrome(service=service, options=options)

    all_reviews = []
    current_url = TARGET_URL
    is_scraping = True

    print("Starting the scraping process...")

    while current_url and is_scraping:
        driver.get(current_url)
        time.sleep(3) # Wait for the page to load

        # --- NEW CODE TO HANDLE COOKIE BANNER ---
        try:
            # Find the button by its ID and click it
            cookie_button = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
            if cookie_button:
                print("Cookie banner found. Clicking 'Accept'.")
                cookie_button.click()
                time.sleep(5) # Wait for the banner to disappear
        except NoSuchElementException:
            print("No cookie banner found, continuing...")
            pass # If no banner is found, just continue
        # --- END OF NEW CODE ---

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        review_cards = soup.find_all('div', class_='styles_cardWrapper__g8amG styles_show__Z8n7u')
        
        if not review_cards:
            print("No more review cards found. Ending scrape.")
            break

        print(f"Found {len(review_cards)} reviews on this page...")

        for card in review_cards:
            review_date_element = card.find('time')
            if not review_date_element or 'datetime' not in review_date_element.attrs:
                continue
            
            review_date_str = review_date_element['datetime']
            review_date = parse_review_date(review_date_str)
            
            if review_date and review_date < START_DATE:
                is_scraping = False
                print(f"Found a review from {review_date}, which is before our start date. Stopping.")
                break

            review_title = card.find('h2', class_='CDS_Typography_appearance-default__dd9b51 CDS_Typography_prettyStyle__dd9b51 CDS_Typography_heading-xs__dd9b51').get_text(strip=True) if card.find('h2') else 'No Title'
            review_body_element = card.find('p', class_='CDS_Typography_appearance-default__dd9b51 CDS_Typography_prettyStyle__dd9b51 CDS_Typography_body-l__dd9b51')
            review_body = review_body_element.get_text(strip=True) if review_body_element else 'No Content'
            rating_element = card.find('div', class_='styles_reviewHeader__iU9Px')
            rating = rating_element['data-service-review-rating'] if rating_element else 'N/A'
            
            all_reviews.append({
                'date': review_date,
                'rating': rating,
                'title': review_title,
                'review_text': review_body
            })

        if not is_scraping:
            break

        next_page_link = soup.find('a', {'name': 'pagination-button-next', 'href': True})
        if next_page_link:
            current_url = 'https://www.trustpilot.com' + next_page_link['href']
            print("Navigating to the next page...")
        else:
            print("No 'next page' button found. Finishing.")
            current_url = None

    driver.quit()
    return all_reviews

def analyze_reviews(reviews_list):
    """Analyzes the list of reviews for T&C issues."""
    if not reviews_list:
        print("No reviews were collected. Analysis cannot be performed.")
        return

    df = pd.DataFrame(reviews_list)
    print(f"\nSuccessfully scraped a total of {len(df)} reviews since {START_DATE}.")

    # 1. Save all reviews to CSV
    df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"All reviews have been saved to '{OUTPUT_CSV_FILE}'")

    # 2. Identify reviews mentioning T&C rigidity
    # These keywords cover cancellation, refunds, changes, policies, etc.
    keywords = [
        'cancel', 'cancellation', 'refund', 'no refund', 'non-refundable',
        'change booking', 'amend', 'modification', 'modify', 'policy',
        'terms', 'conditions', 't&c', 'fee', 'charge', 'voucher', 'credit'
    ]
    
    # Function to check if any keyword is in the review text
    def contains_keyword(text):
        if not isinstance(text, str):
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    df['mentions_tc_issues'] = df['review_text'].apply(contains_keyword)

    # 3. Calculate the percentage
    total_reviews = len(df)
    reviews_with_tc_issues = df['mentions_tc_issues'].sum() # .sum() on a boolean column counts True values

    if total_reviews > 0:
        percentage = (reviews_with_tc_issues / total_reviews) * 100
    else:
        percentage = 0

    print("\n--- Analysis Complete ---")
    print(f"Total 1 & 2-star reviews since {START_DATE}: {total_reviews}")
    print(f"Reviews addressing T&C / rigidity issues: {reviews_with_tc_issues}")
    print(f"Percentage of reviews with T&C issues: {percentage:.2f}%")


if __name__ == '__main__':
    scraped_reviews = scrape_trustpilot()
    analyze_reviews(scraped_reviews)
