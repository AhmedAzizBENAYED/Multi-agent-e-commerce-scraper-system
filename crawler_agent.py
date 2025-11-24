import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
import re
from dataclasses import dataclass
import json


@dataclass
class CrawlerConfig:
    """Configuration for website crawler"""
    base_url: str
    max_depth: int = 2
    max_pages: int = 50
    keywords: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            # Default keywords for product listing pages
            self.keywords = [
                'pc-portable', 'ordinateur', 'laptop', 'portable',
                'gamer', 'informatique', 'computer', 'notebook',
                'ultrabook', 'workstation', 'categorie', 'category',
                'products', 'produits'
            ]


class WebsiteCrawler:
    """Intelligent crawler to find product listing pages"""

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.product_listing_urls: Set[str] = set()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Patterns that indicate product listing pages
        self.listing_patterns = [
            r'/\d+-',  # e.g., /74-pc-portable
            r'category',
            r'categorie',
            r'products',
            r'produits',
            r'pc-portable',
            r'ordinateur',
            r'laptop',
            r'portable',
            r'gamer',
            r'informatique'
        ]

        # Patterns to exclude
        self.exclude_patterns = [
            r'\.pdf$', r'\.jpg$', r'\.png$', r'\.gif$',
            r'/cart', r'/panier', r'/checkout',
            r'/account', r'/compte', r'/login',
            r'/contact', r'/about', r'/mentions-legales',
            r'/cgv', r'/terms', r'/privacy',
            r'facebook\.com', r'twitter\.com', r'instagram\.com'
        ]

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the target domain"""
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.config.base_url)

            # Must be same domain
            if parsed.netloc != base_parsed.netloc:
                return False

            # Check exclude patterns
            for pattern in self.exclude_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False

            return True
        except Exception:
            return False

    def is_product_listing_page(self, url: str, soup: BeautifulSoup) -> bool:
        """Determine if a page is a product listing page"""
        # Check URL patterns
        url_score = 0
        for pattern in self.listing_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                url_score += 1

        # Check page content indicators
        content_score = 0

        # Look for product containers
        product_indicators = [
            '.product-miniature', '.product-item', '.product-container',
            '.products', '#js-product-list', '.product-grid',
            'article[itemtype*="Product"]', '[data-id-product]',
            '[data-product-id]'
        ]

        for indicator in product_indicators:
            elements = soup.select(indicator)
            if len(elements) > 3:  # Multiple products = listing page
                content_score += 2
            elif len(elements) > 0:
                content_score += 1

        # Look for pagination (strong indicator of listing page)
        pagination_selectors = [
            '.pagination', '.page-list', '[class*="pagination"]',
            'nav[aria-label*="pagination"]', '.pages'
        ]

        for selector in pagination_selectors:
            if soup.select_one(selector):
                content_score += 2
                break

        # Look for category/filter elements
        filter_selectors = [
            '.facet', '.filter', '[id*="filter"]',
            '.layered-navigation', '.sidebar-filter'
        ]

        for selector in filter_selectors:
            if soup.select_one(selector):
                content_score += 1
                break

        # Decision: URL score + content score
        total_score = url_score + content_score
        return total_score >= 3

    def extract_links(self, url: str, soup: BeautifulSoup) -> List[str]:
        """Extract all valid links from a page"""
        links = set()

        for anchor in soup.find_all('a', href=True):
            href = anchor['href'].strip()

            # Normalize URL
            full_url = urljoin(url, href)

            # Remove fragments
            full_url = full_url.split('#')[0]

            # Validate
            if self.is_valid_url(full_url):
                links.add(full_url)

        return list(links)

    def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def crawl_page(self, url: str, depth: int = 0) -> List[str]:
        """Recursively crawl a page to find product listing URLs"""
        # Stop conditions
        if depth > self.config.max_depth:
            return []

        if url in self.visited_urls:
            return []

        if len(self.visited_urls) >= self.config.max_pages:
            return []

        print(f"{'  ' * depth}Crawling: {url} (depth: {depth})")
        self.visited_urls.add(url)

        # Fetch page
        soup = self.fetch_page(url)
        if not soup:
            return []

        # Check if this is a product listing page
        if self.is_product_listing_page(url, soup):
            print(f"{'  ' * depth}✓ Found product listing page!")
            self.product_listing_urls.add(url)

        # Extract links for deeper crawling
        links = self.extract_links(url, soup)

        # Prioritize links with keywords
        prioritized_links = []
        other_links = []

        for link in links:
            if link in self.visited_urls:
                continue

            # Check if link contains keywords
            has_keyword = any(
                keyword.lower() in link.lower()
                for keyword in self.config.keywords
            )

            if has_keyword:
                prioritized_links.append(link)
            else:
                other_links.append(link)

        # Crawl prioritized links first (breadth-first for relevant pages)
        for link in prioritized_links[:10]:  # Limit to avoid explosion
            if len(self.visited_urls) >= self.config.max_pages:
                break
            self.crawl_page(link, depth + 1)

        # Crawl other links if we haven't found enough
        if len(self.product_listing_urls) < 5 and depth < self.config.max_depth:
            for link in other_links[:5]:
                if len(self.visited_urls) >= self.config.max_pages:
                    break
                self.crawl_page(link, depth + 1)

        return list(self.product_listing_urls)

    def crawl(self) -> List[str]:
        """Start crawling from base URL"""
        print(f"\nStarting crawl from: {self.config.base_url}")
        print(f"Max depth: {self.config.max_depth}, Max pages: {self.config.max_pages}")
        print("=" * 60)

        self.crawl_page(self.config.base_url, depth=0)

        print("\n" + "=" * 60)
        print(f"Crawl complete!")
        print(f"Pages visited: {len(self.visited_urls)}")
        print(f"Product listing pages found: {len(self.product_listing_urls)}")

        return list(self.product_listing_urls)

    def get_crawl_stats(self) -> Dict:
        """Get statistics about the crawl"""
        return {
            'base_url': self.config.base_url,
            'pages_visited': len(self.visited_urls),
            'product_pages_found': len(self.product_listing_urls),
            'product_listing_urls': list(self.product_listing_urls)
        }


# Configuration for each website
WEBSITE_CONFIGS = {
    'spacenet.tn': {
        'base_url': 'https://spacenet.tn/',
        'keywords': ['pc-portable', 'ordinateur', 'laptop', 'gamer', 'informatique']
    },
    'tunisianet.com.tn': {
        'base_url': 'https://www.tunisianet.com.tn/',
        'keywords': ['pc-portable', 'ordinateur', 'laptop', 'gamer', 'informatique']
    },
    'mytek.tn': {
        'base_url': 'https://www.mytek.tn/',
        'keywords': ['pc-portable', 'ordinateurs-portables', 'laptop', 'informatique']
    }
}


def create_crawler(website_key: str, max_depth: int = 2, max_pages: int = 30) -> WebsiteCrawler:
    """Factory function to create a crawler for a specific website"""
    if website_key not in WEBSITE_CONFIGS:
        raise ValueError(f"Unknown website: {website_key}")

    config_dict = WEBSITE_CONFIGS[website_key]
    config = CrawlerConfig(
        base_url=config_dict['base_url'],
        max_depth=max_depth,
        max_pages=max_pages,
        keywords=config_dict['keywords']
    )

    return WebsiteCrawler(config)


def main():
    """Test the crawler"""
    # Test with one website
    website = 'spacenet.tn'
    print(f"\nTesting crawler for {website}")

    crawler = create_crawler(website, max_depth=2, max_pages=20)
    product_urls = crawler.crawl()

    print("\n" + "=" * 60)
    print("PRODUCT LISTING URLS FOUND:")
    print("=" * 60)
    for i, url in enumerate(product_urls, 1):
        print(f"{i}. {url}")

    # Save results
    stats = crawler.get_crawl_stats()
    with open(f'crawler_results_{website}.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to crawler_results_{website}.json")


if __name__ == "__main__":
    main()