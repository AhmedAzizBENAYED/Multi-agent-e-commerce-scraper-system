import json
import re
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict


@dataclass
class Product:
    """Product data structure"""
    name: str
    url: str
    product_id: Optional[str]
    regular_price: Optional[str]
    final_price: str
    discount: Optional[str]
    image_url: Optional[str]
    sku: Optional[str] = None
    description: Optional[str] = None
    source_website: str = ""


class EcommerceScraper:
    """Universal e-commerce scraper for Tunisian websites"""

    def __init__(self, selectors_file: str = "ecommerce_selectors.json"):
        """Initialize scraper with selectors configuration"""
        with open(selectors_file, 'r', encoding='utf-8') as f:
            self.selectors_config = json.load(f)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def identify_website(self, url: str) -> Optional[str]:
        """Identify which website configuration to use based on URL"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        for site_key, site_config in self.selectors_config.items():
            if site_config['domain'] in domain:
                return site_key

        return None

    def fetch_page(self, url: str, use_playwright: bool = False) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page; fallback to Playwright for JS sites"""
        if use_playwright:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                print("Playwright not installed. Install with 'pip install playwright'")
                return None

            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url)
                    # Wait for products to load (adjust selector if needed)
                    page.wait_for_selector(".product-container, .product-item, .product-miniature", timeout=10000)
                    html = page.content()
                    browser.close()
                return BeautifulSoup(html, 'html.parser')
            except Exception as e:
                print(f"Playwright fetch failed: {e}")
                return None
        else:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                return None

    def extract_text(self, element, selector: str) -> Optional[str]:
        """Safely extract text from an element using selector"""
        if not element:
            return None

        # Handle multiple selectors separated by comma
        selectors = [s.strip() for s in selector.split(',')]

        for sel in selectors:
            try:
                found = element.select_one(sel)
                if found:
                    return found.get_text(strip=True)
            except Exception:
                continue

        return None

    def extract_attribute(self, element, selector: str, attribute: str) -> Optional[str]:
        """Safely extract attribute from an element"""
        if not element:
            return None

        selectors = [s.strip() for s in selector.split(',')]

        for sel in selectors:
            try:
                found = element.select_one(sel)
                if found and found.has_attr(attribute):
                    return found[attribute]
            except Exception:
                continue

        return None

    def extract_link(self, element, selector: str, base_url: str) -> Optional[str]:
        """Extract and normalize product link"""
        if not element:
            return None

        selectors = [s.strip() for s in selector.split(',')]

        for sel in selectors:
            try:
                # First try to find anchor tag
                found = element.select_one(sel)
                if found:
                    # If found element is an anchor
                    if found.name == 'a' and found.has_attr('href'):
                        href = found['href']
                    # If found element contains an anchor
                    else:
                        anchor = found.find('a', href=True)
                        if anchor:
                            href = anchor['href']
                        else:
                            continue

                    # Normalize URL
                    if href:
                        href = href.strip()
                        if href.startswith('http'):
                            return href
                        else:
                            return urljoin(base_url, href)
            except Exception as e:
                continue

        # Fallback: try to find any anchor in the element
        try:
            anchor = element.find('a', href=True)
            if anchor:
                href = anchor['href'].strip()
                if href.startswith('http'):
                    return href
                else:
                    return urljoin(base_url, href)
        except Exception:
            pass

        return None

    def clean_price(self, price_text: Optional[str]) -> Optional[str]:
        """Clean and format price text"""
        if not price_text:
            return None

        # Remove extra whitespace and normalize
        price_text = re.sub(r'\s+', ' ', price_text.strip())
        return price_text

    def calculate_discount(self, regular_price: str, final_price: str) -> Optional[str]:
        """Calculate discount amount or percentage"""
        try:
            # Extract numeric values
            regular = float(re.sub(r'[^\d.]', '', regular_price.replace(',', '').replace(' ', '')))
            final = float(re.sub(r'[^\d.]', '', final_price.replace(',', '').replace(' ', '')))

            if regular > final:
                discount_amount = regular - final
                discount_percent = ((regular - final) / regular) * 100
                return f"-{discount_amount:.3f} DT ({discount_percent:.1f}%)"
        except (ValueError, ZeroDivisionError):
            pass

        return None

    def is_product_on_promotion(self, product_element, site_config: dict) -> bool:
        """Check if product is on promotion based on site configuration"""
        promotion_indicator = site_config.get('promotion_indicator', {})
        has_both = promotion_indicator.get('has_both', [])

        if not has_both:
            return False

        selectors = site_config['selectors']

        # Check if all required elements exist
        for indicator in has_both:
            selector = selectors.get(indicator)
            if not selector:
                continue

            # Try all selector variations
            found = False
            for sel in selector.split(','):
                if product_element.select_one(sel.strip()):
                    found = True
                    break

            if not found:
                return False

        return True

    def extract_product_data(self, product_element, site_config: dict, base_url: str) -> Optional[Product]:
        """Extract product data from a product element"""
        selectors = site_config['selectors']

        # Extract product name
        name = self.extract_text(product_element, selectors['product_name'])
        if not name:
            return None

        # Extract product URL using improved method
        product_url = self.extract_link(product_element, selectors['product_link'], base_url)

        # Extract product ID
        product_id = None
        if 'product_id' in selectors:
            product_id = self.extract_attribute(
                product_element,
                selectors['product_id'],
                'data-id-product'
            ) or self.extract_attribute(
                product_element,
                selectors['product_id'],
                'data-product-id'
            )

        # Extract prices
        regular_price = self.clean_price(
            self.extract_text(product_element, selectors.get('regular_price', ''))
        )
        final_price = self.clean_price(
            self.extract_text(product_element, selectors['final_price'])
        )

        if not final_price:
            return None

        # Calculate discount
        discount = None
        if regular_price and final_price:
            discount = self.calculate_discount(regular_price, final_price)

        # Extract discount amount if available (for SpaceNet)
        if 'discount_amount' in selectors:
            discount_text = self.extract_text(product_element, selectors['discount_amount'])
            if discount_text:
                discount = discount_text

        # Extract image URL
        image_url = self.extract_attribute(
            product_element,
            selectors['product_image'],
            'src'
        ) or self.extract_attribute(
            product_element,
            selectors['product_image'],
            'data-src'
        )

        # Normalize image URL
        if image_url and not image_url.startswith('http'):
            image_url = urljoin(base_url, image_url)

        # Extract additional fields
        sku = None
        if 'product_sku' in selectors:
            sku = self.extract_text(product_element, selectors['product_sku'])

        description = None
        if 'product_description' in selectors:
            description = self.extract_text(product_element, selectors['product_description'])

        return Product(
            name=name,
            url=product_url or "",
            product_id=product_id,
            regular_price=regular_price,
            final_price=final_price,
            discount=discount,
            image_url=image_url,
            sku=sku,
            description=description,
            source_website=site_config['name']
        )

    def scrape_promotions(self, url: str, use_playwright: bool = False) -> List[Dict]:
        """Scrape all products on promotion from a given URL"""
        # Identify website
        site_key = self.identify_website(url)
        if not site_key:
            print(f"Website not recognized: {url}")
            return []

        site_config = self.selectors_config[site_key]
        print(f"Scraping {site_config['name']}...")

        # Fetch page
        soup = self.fetch_page(url, use_playwright=use_playwright)

        if not soup:
            return []

        # Find product list container
        product_list = None
        for selector in site_config['selectors']['product_list'].split(','):
            product_list = soup.select_one(selector.strip())
            if product_list:
                break

        if not product_list:
            print("Product list container not found")
            return []

        # Find all product items
        product_elements = []
        for selector in site_config['selectors']['product_item'].split(','):
            product_elements = product_list.select(selector.strip())
            if product_elements:
                break

        # Try alternative selector if needed
        if not product_elements and 'product_item_alt' in site_config['selectors']:
            for selector in site_config['selectors']['product_item_alt'].split(','):
                product_elements = product_list.select(selector.strip())
                if product_elements:
                    break

        print(f"Found {len(product_elements)} products")

        # Extract products on promotion
        promotions = []
        for element in product_elements:
            if self.is_product_on_promotion(element, site_config):
                product = self.extract_product_data(element, site_config, url)
                if product:
                    promotions.append(asdict(product))

        print(f"Found {len(promotions)} products on promotion")
        return promotions

    def save_results(self, products: List[Dict], output_file: str = "promotions.json"):
        """Save scraped products to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {output_file}")


def main():
    """Main function to demonstrate usage"""
    scraper = EcommerceScraper("ecommerce_selectors.json")

    # Example URLs
    test_urls = [
        "https://spacenet.tn/74-pc-portable-tunisie?page=2",
        "https://www.tunisianet.com.tn/681-pc-portable-gamer",
        "https://www.mytek.tn/informatique/ordinateurs-portables/pc-portable.html"
    ]

    # Scrape each URL
    all_promotions = []
    for url in test_urls:
        print(f"\n{'=' * 60}")
        print(f"Scraping: {url}")
        print('=' * 60)

        # Use Playwright for MyTek if needed
        use_pw = "mytek.tn" in url
        promotions = scraper.scrape_promotions(url, use_playwright=use_pw)
        all_promotions.extend(promotions)

        # Display results
        if promotions:
            print(f"\nProducts on promotion:")
            for i, product in enumerate(promotions[:5], 1):  # Show first 5
                print(f"\n{i}. {product['name']}")
                print(f"   Regular Price: {product['regular_price']}")
                print(f"   Final Price: {product['final_price']}")
                print(f"   Discount: {product['discount']}")
                print(f"   URL: {product['url']}")

    # Save all results
    if all_promotions:
        scraper.save_results(all_promotions, "all_promotions.json")
        print(f"\n{'=' * 60}")
        print(f"Total promotions found: {len(all_promotions)}")
        print('=' * 60)


if __name__ == "__main__":
    main()