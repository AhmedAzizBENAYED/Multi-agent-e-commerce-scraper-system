# 🤖 Multi-Agent E-Commerce Promotion Scraper

An intelligent multi-agent system built with LangGraph and LangChain that automatically crawls and scrapes Tunisian e-commerce websites to find products on promotion. **Works 100% locally with Ollama!**

## 🏗️ System Architecture

The system consists of 4 specialized agents working in a pipeline:

```
┌─────────────────┐      ┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  Website        │ ───> │  Crawler    │ ───> │  Scraper    │ ───> │  Aggregator  │
│  Selector Agent │      │  Agent      │      │  Agent      │      │  Agent       │
└─────────────────┘      └─────────────┘      └─────────────┘      └──────────────┘
     User Input          Find Product         Extract Product      Compile & Save
                         Listing Pages        Promotions           Results
```

### Agent Roles

1. **🌐 Website Selector Agent**: Presents available websites and lets users choose which ones to scrape
2. **🕷️ Crawler Agent**: Intelligently crawls each website to discover product listing pages using heuristics
3. **🔍 Scraper Agent**: Extracts product information from discovered pages, filtering for promotions only
4. **📊 Aggregator Agent**: Compiles results, generates reports, and saves data to JSON files

## 🌐 Supported Websites

- **SpaceNet** (spacenet.tn) - PC Portables, Gaming, Electronics
- **TunisiaNet** (tunisianet.com.tn) - Computers, Laptops, Gaming
- **MyTek** (mytek.tn) - IT Equipment, Laptops, Electronics

## ⚡ Features

- ✅ **100% Local** - Works with local LLMs via Ollama (no API keys needed!)
- ✅ **Multi-Agent Architecture** - Specialized agents for different tasks
- ✅ **Intelligent Crawling** - Finds product pages automatically
- ✅ **Promotion Detection** - Only returns products on sale
- ✅ **Multiple Website Support** - Scrape one or all websites
- ✅ **JSON Export** - Results saved in structured format
- ✅ **Detailed Reports** - Comprehensive scraping statistics
- ✅ **Error Handling** - Robust with fallbacks
- ✅ **No API Costs** - Everything runs on your machine

## 📋 Prerequisites

### 1. Python 3.8+
```bash
python --version  # Should be 3.8 or higher
```

### 2. Ollama (Optional but Recommended)
For enhanced AI capabilities, install Ollama:

**Linux/macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [ollama.ai/download](https://ollama.ai/download)

**Pull a model:**
```bash
ollama pull llama3.2
# or
ollama pull mistral
# or
ollama pull phi3
```

### 3. Playwright (Optional)
For JavaScript-heavy sites like MyTek:
```bash
pip install playwright
playwright install chromium
```

## 🚀 Installation

1. **Clone or download the project files**

2. **Create a virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Optional - Install Playwright:**
```bash
playwright install chromium
```

## 📁 Project Structure

```
.
├── ecommerce_selectors.json    # CSS selectors for each website
├── crawler_agent.py            # Crawler agent implementation
├── promo_scraper.py           # Scraper agent implementation
├── multi_agent_system.py      # Main multi-agent orchestrator
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🎯 Usage

### Quick Start

Run the complete multi-agent system:

```bash
python multi_agent_system.py
```

The system will:
1. Ask if you want to use local LLM (optional)
2. Show available websites
3. Let you select which websites to scrape
4. Crawl and find product pages automatically
5. Scrape promotions from found pages
6. Generate comprehensive reports

### Example Session

```
INITIALIZATION
================================================================================

Do you want to use local LLM (Ollama) for enhanced intelligence?
This requires Ollama to be installed and running.
Download from: https://ollama.ai/

Use LLM? (y/n, default=n): n

╔══════════════════════════════════════════════════════════════════════════════╗
║               🤖 MULTI-AGENT PROMOTION SCRAPER                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

• Running without LLM (rule-based mode)

════════════════════════════════════════════════════════════════════════════════
🌐 WEBSITE SELECTOR AGENT
════════════════════════════════════════════════════════════════════════════════

Available e-commerce websites:
  1. spacenet.tn
     URL: https://spacenet.tn/
     Categories: pc-portable, ordinateur, laptop...

  2. tunisianet.com.tn
     URL: https://www.tunisianet.com.tn/
     Categories: pc-portable, ordinateur, laptop...

  3. mytek.tn
     URL: https://www.mytek.tn/
     Categories: pc-portable, ordinateurs-portables, laptop...

Enter the numbers of websites to scrape (comma-separated) or 'all':
Examples: '1,2' or 'all' or '1'

→ Your selection: all

✓ Selected all 3 websites
```

### Individual Agent Testing

**Test Crawler Only:**
```bash
python crawler_agent.py
```

**Test Scraper Only:**
```bash
python promo_scraper.py
```

## 📤 Output Files

After running, you'll get:

1. **all_promotions_final.json**
   - List of all products on promotion
   - Includes: name, prices, discount, URL, image, etc.

2. **scraping_report.json**
   - Detailed statistics
   - URLs crawled
   - Products by website
   - Full product data

### Example Output Structure

```json
{
  "name": "PC Portable HP 15-fd0297nk",
  "url": "https://www.mytek.tn/pc-portable-hp...",
  "product_id": "12345",
  "regular_price": "829,000 DT",
  "final_price": "789,000 DT",
  "discount": "-40.000 DT (4.8%)",
  "image_url": "https://...",
  "source_website": "MyTek"
}
```

## ⚙️ Configuration

### Adjust Crawling Parameters

Edit in `multi_agent_system.py`:
```python
crawler = create_crawler(
    website, 
    max_depth=2,      # How deep to crawl (1-3 recommended)
    max_pages=30      # Maximum pages to visit
)
```

### Custom CSS Selectors

Edit `ecommerce_selectors.json` to add new websites or update selectors:

```json
{
  "newsite.com": {
    "domain": "newsite.com",
    "name": "NewSite",
    "selectors": {
      "product_item": ".product",
      "product_name": ".product-title",
      "regular_price": ".old-price",
      "final_price": ".new-price"
    }
  }
}
```

## 🔧 Advanced Usage

### Using Local LLM

1. **Start Ollama:**
```bash
ollama serve
```

2. **Run with LLM support:**
```bash
python multi_agent_system.py
# Select 'y' when asked about using LLM
```

The LLM can help with:
- Better understanding of product pages
- Intelligent URL filtering
- Enhanced error recovery

### Adding New Websites

1. Add website config to `WEBSITE_CONFIGS` in `crawler_agent.py`
2. Add CSS selectors to `ecommerce_selectors.json`
3. Test with crawler first, then full system

## 🐛 Troubleshooting

### "Website not recognized"
- Check if domain is in `ecommerce_selectors.json`
- Ensure URL format matches configuration

### "No products found"
- Verify CSS selectors are still valid
- Website might have changed structure
- Try with Playwright for JS-heavy sites

### Playwright errors
```bash
playwright install chromium
```

### Ollama connection failed
```bash
# Start Ollama server
ollama serve

# In another terminal
ollama pull llama3.2
```

### Slow scraping
- Reduce `max_pages` in crawler config
- Use fewer websites at once
- Some sites have rate limiting

## 📊 Performance Tips

1. **Start Small**: Test with one website first
2. **Adjust Depth**: `max_depth=1` for faster results
3. **Limit Pages**: `max_pages=20` for quick tests
4. **Use Playwright Selectively**: Only for sites that need it
5. **Run During Off-Peak**: Some sites may rate-limit

## 🤝 Contributing

To add support for a new website:

1. Inspect the website HTML
2. Identify CSS selectors for products
3. Add configuration to `ecommerce_selectors.json`
4. Test with the scraper
5. Update crawler keywords if needed

## 📝 License

This project is for educational purposes. Please respect website terms of service and use responsibly.

## ⚠️ Disclaimer

- This tool is for personal use only
- Respect robots.txt and rate limits
- Don't overload servers with requests
- Some websites may block scrapers
- Always check website terms of service

## 🙋 FAQ

**Q: Do I need an API key?**
A: No! Everything runs locally with Ollama.

**Q: Which LLM model should I use?**
A: Start with `llama3.2` (3B) for speed, or `mistral` for better reasoning.

**Q: How long does it take?**
A: Depends on settings. Typically 2-5 minutes per website.

**Q: Can I scrape other websites?**
A: Yes! Add their selectors to `ecommerce_selectors.json`.

**Q: Is this legal?**
A: Scraping public data is generally legal, but check each site's terms of service.

**Q: Can I schedule this to run automatically?**
A: Yes! Use cron (Linux/Mac) or Task Scheduler (Windows).

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all prerequisites are installed
3. Test individual agents first
4. Check if website structure changed

---

**Happy Scraping! 🎉**
