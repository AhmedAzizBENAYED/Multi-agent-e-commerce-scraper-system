from typing import TypedDict, Annotated, List, Dict
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from crawler_agent import create_crawler, WEBSITE_CONFIGS
from promo_scraper import EcommerceScraper
import json


# Define the state of our graph
class AgentState(TypedDict):
    """State shared between all agents"""
    messages: Annotated[List, operator.add]
    selected_websites: List[str]
    crawled_urls: Dict[str, List[str]]
    scraped_products: List[Dict]
    current_step: str
    error: str


class PromoScraperAgent:
    """Multi-agent system for scraping promotions from e-commerce sites"""

    def __init__(self, use_llm: bool = False, model_name: str = "llama3.2"):
        """
        Initialize the multi-agent system

        Args:
            use_llm: Whether to use LLM for intelligent decisions (requires Ollama)
            model_name: Ollama model to use (llama3.2, mistral, etc.)
        """
        # Initialize LLM (optional, for more intelligent decision making)
        self.use_llm = use_llm
        if use_llm:
            try:
                self.llm = ChatOllama(
                    model=model_name,
                    temperature=0
                )
                print(f"✓ Using local LLM: {model_name}")
            except Exception as e:
                print(f"⚠ Failed to initialize LLM: {e}")
                print("  Make sure Ollama is installed and running:")
                print("  - Install: https://ollama.ai/download")
                print("  - Run: ollama pull llama3.2")
                self.use_llm = False
                self.llm = None
        else:
            self.llm = None

        # Initialize tools
        self.scraper = EcommerceScraper("ecommerce_selectors.json")

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes (agents)
        workflow.add_node("website_selector", self.website_selector_node)
        workflow.add_node("crawler", self.crawler_node)
        workflow.add_node("scraper", self.scraper_node)
        workflow.add_node("aggregator", self.aggregator_node)

        # Define edges (workflow)
        workflow.set_entry_point("website_selector")
        workflow.add_edge("website_selector", "crawler")
        workflow.add_edge("crawler", "scraper")
        workflow.add_edge("scraper", "aggregator")
        workflow.add_edge("aggregator", END)

        return workflow.compile()

    def website_selector_node(self, state: AgentState) -> AgentState:
        """Agent 1: Website Selection - Let user choose websites"""
        print("\n" + "=" * 80)
        print("🌐 WEBSITE SELECTOR AGENT")
        print("=" * 80)

        available_websites = list(WEBSITE_CONFIGS.keys())

        print("\nAvailable e-commerce websites:")
        for i, website in enumerate(available_websites, 1):
            config = WEBSITE_CONFIGS[website]
            print(f"  {i}. {website}")
            print(f"     URL: {config['base_url']}")
            print(f"     Categories: {', '.join(config['keywords'][:3])}...\n")

        # Get user selection
        print("Enter the numbers of websites to scrape (comma-separated) or 'all':")
        print("Examples: '1,2' or 'all' or '1'")

        user_input = input("\n→ Your selection: ").strip().lower()

        selected_websites = []
        if user_input == 'all':
            selected_websites = available_websites
            print(f"\n✓ Selected all {len(selected_websites)} websites")
        else:
            try:
                indices = [int(x.strip()) - 1 for x in user_input.split(',')]
                selected_websites = [
                    available_websites[i]
                    for i in indices
                    if 0 <= i < len(available_websites)
                ]

                if not selected_websites:
                    print("⚠ Invalid selection. Defaulting to all websites.")
                    selected_websites = available_websites
                else:
                    print(f"\n✓ Selected: {', '.join(selected_websites)}")

            except (ValueError, IndexError):
                print("⚠ Invalid input format. Defaulting to all websites.")
                selected_websites = available_websites

        state["selected_websites"] = selected_websites
        state["current_step"] = "website_selection_complete"
        state["messages"].append(
            AIMessage(content=f"Selected {len(selected_websites)} websites: {', '.join(selected_websites)}")
        )

        return state

    def crawler_node(self, state: AgentState) -> AgentState:
        """Agent 2: Crawler - Find product listing pages"""
        print("\n" + "=" * 80)
        print("🕷️  CRAWLER AGENT")
        print("=" * 80)

        crawled_urls = {}

        for website in state["selected_websites"]:
            print(f"\n{'─' * 80}")
            print(f"Crawling: {website}")
            print('─' * 80)

            try:
                # Create crawler
                crawler = create_crawler(website, max_depth=2, max_pages=30)

                # Crawl website
                product_urls = crawler.crawl()

                # Store results
                crawled_urls[website] = product_urls

                print(f"\n✓ Found {len(product_urls)} product listing pages for {website}")

            except Exception as e:
                print(f"\n✗ Error crawling {website}: {e}")
                crawled_urls[website] = []
                state["error"] = f"Crawler error for {website}: {str(e)}"

        state["crawled_urls"] = crawled_urls
        state["current_step"] = "crawling_complete"

        total_urls = sum(len(urls) for urls in crawled_urls.values())
        state["messages"].append(
            AIMessage(
                content=f"Crawling complete. Found {total_urls} product listing pages across {len(state['selected_websites'])} websites")
        )

        return state

    def scraper_node(self, state: AgentState) -> AgentState:
        """Agent 3: Scraper - Extract products on promotion"""
        print("\n" + "=" * 80)
        print("🔍 SCRAPER AGENT")
        print("=" * 80)

        all_products = []

        for website, urls in state["crawled_urls"].items():
            if not urls:
                print(f"\n⚠ No URLs to scrape for {website}")
                continue

            print(f"\n{'─' * 80}")
            print(f"Scraping: {website} ({len(urls)} pages)")
            print('─' * 80)

            website_products = []

            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] {url}")

                try:
                    # Scrape products (use Playwright for MyTek)
                    use_playwright = website == "mytek.tn"
                    products = self.scraper.scrape_promotions(url, use_playwright=use_playwright)

                    website_products.extend(products)

                    if products:
                        print(f"  ✓ Found {len(products)} products on promotion")
                    else:
                        print(f"  • No promotions found")

                except Exception as e:
                    print(f"  ✗ Error: {e}")

            all_products.extend(website_products)
            print(f"\n{'─' * 40}")
            print(f"✓ {website} Total: {len(website_products)} products on promotion")
            print('─' * 40)

        state["scraped_products"] = all_products
        state["current_step"] = "scraping_complete"
        state["messages"].append(
            AIMessage(content=f"Scraping complete. Found {len(all_products)} total products on promotion")
        )

        return state

    def aggregator_node(self, state: AgentState) -> AgentState:
        """Agent 4: Aggregator - Compile and save results"""
        print("\n" + "=" * 80)
        print("📊 AGGREGATOR AGENT")
        print("=" * 80)

        products = state["scraped_products"]

        if not products:
            print("\n⚠ No products found on promotion")
            state["current_step"] = "complete"
            return state

        # Group by website
        products_by_website = {}
        for product in products:
            website = product['source_website']
            if website not in products_by_website:
                products_by_website[website] = []
            products_by_website[website].append(product)

        # Display summary
        print("\n" + "=" * 80)
        print("📈 RESULTS SUMMARY")
        print("=" * 80)

        for website, prods in products_by_website.items():
            print(f"\n🏪 {website}: {len(prods)} products")
            print("─" * 40)

            # Show top 5 products
            for i, product in enumerate(prods[:5], 1):
                print(f"\n  {i}. {product['name'][:70]}...")
                print(f"     💰 Regular: {product['regular_price']} → Final: {product['final_price']}")
                print(f"     🎯 Discount: {product['discount']}")

            if len(prods) > 5:
                print(f"\n  ... and {len(prods) - 5} more products")

        # Save results
        output_file = "all_promotions_final.json"
        self.scraper.save_results(products, output_file)

        # Create detailed report
        report = {
            'summary': {
                'total_products': len(products),
                'websites_scraped': len(state['selected_websites']),
                'products_by_website': {
                    website: len(prods)
                    for website, prods in products_by_website.items()
                },
                'total_urls_crawled': sum(len(urls) for urls in state['crawled_urls'].values())
            },
            'crawled_urls': state['crawled_urls'],
            'products': products
        }

        report_file = "scraping_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 80}")
        print("💾 FILES SAVED")
        print('=' * 80)
        print(f"✓ Products: {output_file}")
        print(f"✓ Detailed report: {report_file}")

        state["current_step"] = "complete"
        state["messages"].append(
            AIMessage(content=f"Aggregation complete. {len(products)} products saved")
        )

        return state

    def run(self):
        """Execute the multi-agent workflow"""
        print("\n" + "╔" + "=" * 78 + "╗")
        print("║" + " " * 15 + "🤖 MULTI-AGENT PROMOTION SCRAPER" + " " * 31 + "║")
        print("╚" + "=" * 78 + "╝")

        if self.use_llm:
            print("\n✓ Running with local LLM support")
        else:
            print("\n• Running without LLM (rule-based mode)")

        # Initialize state
        initial_state = AgentState(
            messages=[HumanMessage(content="Start scraping promotions")],
            selected_websites=[],
            crawled_urls={},
            scraped_products=[],
            current_step="init",
            error=""
        )

        # Run the graph
        try:
            final_state = self.graph.invoke(initial_state)

            print("\n" + "╔" + "=" * 78 + "╗")
            print("║" + " " * 28 + "✅ WORKFLOW COMPLETE!" + " " * 28 + "║")
            print("╚" + "=" * 78 + "╝")

            print(f"\n📊 Final Statistics:")
            print(f"   • Websites: {len(final_state['selected_websites'])}")
            print(f"   • URLs crawled: {sum(len(urls) for urls in final_state['crawled_urls'].values())}")
            print(f"   • Products found: {len(final_state['scraped_products'])}")

            return final_state

        except Exception as e:
            print(f"\n❌ Error during workflow execution: {e}")
            raise


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("INITIALIZATION")
    print("=" * 80)

    # Ask user if they want to use LLM
    print("\nDo you want to use local LLM (Ollama) for enhanced intelligence?")
    print("This requires Ollama to be installed and running.")
    print("Download from: https://ollama.ai/")

    use_llm_input = input("\nUse LLM? (y/n, default=n): ").strip().lower()
    use_llm = use_llm_input in ['y', 'yes']

    model_name = "llama3.2"
    if use_llm:
        print("\nAvailable models: llama3.2, mistral, phi3, etc.")
        model_input = input(f"Model name (default={model_name}): ").strip()
        if model_input:
            model_name = model_input

    # Initialize the multi-agent system
    agent_system = PromoScraperAgent(use_llm=use_llm, model_name=model_name)

    # Run the workflow
    result = agent_system.run()

    print("\n" + "=" * 80)
    print("🎉 All done! Check the generated JSON files for results.")
    print("=" * 80)


if __name__ == "__main__":
    main()