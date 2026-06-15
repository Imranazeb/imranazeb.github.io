import json
import yaml

import yfinance as yf

from custom_agent import analyze
from database import (
    StockData, create_stock_data, stock_exists, stock_reviewed_already, update_reviewed_date, 
    not_reviewed_recently)

from sec_filing import get_8K_filings
from utils.logs import logger

from datetime import datetime

count = 30

# most_active = yf.screen("most_actives", count=count or 10)
day_gainers = yf.screen("day_gainers", count=count or 10)


sorted_day_gainers = sorted(
    day_gainers["quotes"], key=lambda x: x["regularMarketChangePercent"], reverse=True
)


def print_stock_info():
    for stock in sorted_day_gainers:
        print(
            stock["symbol"],
            stock["regularMarketVolume"],
            stock["regularMarketPrice"],
            stock["shortName"],
            stock["regularMarketDayHigh"],
            stock["regularMarketDayLow"],
            stock["regularMarketChangePercent"],
        )


def get_company_info(stock):
    # Limit to first 5 to avoid rate limits
    symbol = stock["symbol"]
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # TODO handle NA logic for website, sector, industry
    website = info.get("website", "N/A")
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")

    return {
        "url": website,
        "sector": sector,
        "industry": industry,
    }


def parse_stock_data(stock):
    return StockData(
        symbol=stock["symbol"],
        name=stock["shortName"],
        price=stock["regularMarketPrice"],
        url=get_company_info(stock)["url"],
        sector=get_company_info(stock)["sector"],
        industry=get_company_info(stock)["industry"],
    )


def find_unreviewed_stocks():
    for stock in sorted_day_gainers:
        symbol = stock["symbol"]

        # Global rule: Skip any stock reviewed within 3 days
        if not not_reviewed_recently(symbol, days_threshold=3):
            continue

        if major_increase_in_price(stock):
            logger.info(f"Found stock with major price increase: {symbol}")
            return parse_stock_data(stock)

        elif not stock_exists(symbol) or not stock_reviewed_already(symbol):
            logger.info(f"Found unreviewed stock: {symbol}")
            return parse_stock_data(stock)
        
        elif not_reviewed_recently(symbol, days_threshold=30):
            logger.info(f"Found stock that was not reviewed in the last 30 days: {symbol}")
            return parse_stock_data(stock)
    return None


def major_increase_in_price(stock):
    change_percent = stock["regularMarketChangePercent"]
    return change_percent and change_percent > 5.0



def get_agent_analysis():
    unreviewed_stock = find_unreviewed_stocks()

    if unreviewed_stock:
        # Get the original stock data with all details

        last_filling = get_8K_filings(unreviewed_stock.symbol)
        last_filing_title = "N/A"
        last_filing_url = "N/A"

        if last_filling:
            last_filing_title = last_filling["title"]
            last_filing_url = last_filling["url"]

        original_stock = next(
            (s for s in sorted_day_gainers if s["symbol"] == unreviewed_stock.symbol),
            None,
        )

        if original_stock:
            schema = """
            {
                "title": "Engaging blog post title (50-60 characters)",
                "meta_description": "SEO-friendly description (150-160 characters)",
                "introduction": "Hook paragraph explaining why this stock is interesting today",
                "key_metrics": {
                    "price_change_percent": "Formatted percentage with context",
                    "volume_analysis": "What the volume indicates",
                    "price_movement": "Analysis of high/low range"
                },
                "main_analysis": [
                    "Paragraph 1: Company overview and sector context",
                ],
                "sec_filings": {
                    "last_8k_filing": last_filing_title,
                    "filing_url": last_filing_url
                },
                "conclusion": "State this is not financial advice",
                "tags": ["stock symbol", "sector name"]
            }
            """

            prompt = f"""Write an informative, engaging blog post about today's stock market mover.

    Stock Information:
    - Symbol: {unreviewed_stock.symbol}
    - Company: {unreviewed_stock.name}
    - Sector: {unreviewed_stock.sector}
    - Industry: {unreviewed_stock.industry if hasattr(unreviewed_stock, "industry") else "N/A"}
    - Current Price: ${original_stock["regularMarketPrice"]:.2f}
    - Day's Change: {original_stock["regularMarketChangePercent"]:.2f}%
    - Day High: ${original_stock["regularMarketDayHigh"]:.2f}
    - Day Low: ${original_stock["regularMarketDayLow"]:.2f}
    - Volume: {original_stock["regularMarketVolume"]:,}
    - Website: {unreviewed_stock.url}
    - Last 8-K Filing: {last_filing_title} 
    - Filing URL: {last_filing_url}

    Requirements:
    1. Write in an informative but accessible tone for retail investors
    2. Focus on why the stock moved significantly today
    3. Provide context about the company's sector and industry trends
    4. Avoid making specific buy/sell recommendations
    5. Use the exact metrics provided above
    6. Keep paragraphs concise (3-4 sentences each)
    7. For tags, use exactly two values: "{unreviewed_stock.symbol}" and "{unreviewed_stock.sector}"
    8. DO NOT mention or discuss SEC filings in the main analysis - the filing link will be provided separately at the end

    Return your response in the following JSON format:
    {schema}"""

            analysis_result = analyze(prompt)
            
            # Return both the analysis and stock data for post creation
            return {
                "analysis": analysis_result,
                "stock": unreviewed_stock,
                "last_filing_title": last_filing_title,
                "last_filing_url": last_filing_url,
                "sorted_day_gainers": sorted_day_gainers
            }
        else:
            logger.error(
                f"Could not find original stock data for {unreviewed_stock.symbol}"
            )
            return None
    else:
        logger.info("No unreviewed stocks found")
        return None


def create_blog_post(result):
    """Create a Chirpy-formatted blog post with hyperlinks"""
    if not result:
        logger.info("No result to create blog post")
        return
    
    analysis = result["analysis"]
    stock = result["stock"]
    filing_title = result["last_filing_title"]
    filing_url = result["last_filing_url"]
    
    # Build markdown content with hyperlinks
    content_parts = []
    
    # Introduction
    content_parts.append(analysis["introduction"])
    content_parts.append("")  # blank line
    
    # Company Info with hyperlink
    if stock.url and stock.url != "N/A":
        content_parts.append(f"## About {stock.name}")
        content_parts.append(f"[{stock.name}]({stock.url}) operates in the {stock.sector} sector, specifically within the {stock.industry} industry.")
        content_parts.append("")
    
    # Key Metrics
    content_parts.append("## Key Metrics")
    key_metrics = analysis.get("key_metrics", {})
    if key_metrics:
        content_parts.append(f"- **Price Change:** {key_metrics.get('price_change_percent', 'N/A')}")
        content_parts.append(f"- **Volume Analysis:** {key_metrics.get('volume_analysis', 'N/A')}")
        content_parts.append(f"- **Price Movement:** {key_metrics.get('price_movement', 'N/A')}")
        content_parts.append("")
    
    # Main Analysis
    content_parts.append("## Analysis")
    main_analysis = analysis.get("main_analysis", [])
    if isinstance(main_analysis, list):
        for paragraph in main_analysis:
            content_parts.append(paragraph)
            content_parts.append("")
    else:
        content_parts.append(str(main_analysis))
        content_parts.append("")
    
    # SEC Filings with hyperlink
    if filing_url and filing_url != "N/A" and filing_title and filing_title != "N/A":
        content_parts.append("## Recent SEC Filings")
        content_parts.append(f"Latest 8-K Filing: [{filing_title}]({filing_url})")
        content_parts.append("")
    
    # Conclusion
    content_parts.append("## Disclaimer")
    content_parts.append(analysis.get("conclusion", "This is not financial advice. Always do your own research before making investment decisions."))
    content_parts.append("")
    
    # Other Notable Movers
    content_parts.append("## Other Notable Movers")
    top_movers = result.get("sorted_day_gainers", [])
    # Get top 3 stocks excluding the main stock
    other_stocks = [s for s in top_movers if s["symbol"] != stock.symbol][:3]
    for mover in other_stocks:
        percent_change = mover.get("regularMarketChangePercent", 0)
        company_info = get_company_info(mover)
        website = company_info.get("url", "N/A")
        
        # Create hyperlink if website exists
        if website and website != "N/A":
            symbol_text = f"[{mover['symbol']}]({website})"
        else:
            symbol_text = mover['symbol']
        
        content_parts.append(f"- **{symbol_text}** ({mover.get('shortName', 'N/A')}): +{percent_change:.2f}%")
    
    # Build YAML frontmatter
    frontmatter_data = {
        'title': analysis["title"],
        'date': datetime.now(),
        'categories': ["Stock Analysis"],
        'tags': analysis.get("tags", [stock.symbol, stock.sector])
    }
    
    # Create full markdown content with frontmatter
    frontmatter_yaml = yaml.dump(frontmatter_data, allow_unicode=True, sort_keys=False)
    markdown_content = f"---\n{frontmatter_yaml}---\n\n{chr(10).join(content_parts)}"
    
    # Save to _posts directory with sanitized filename
    date_str = datetime.now().strftime('%Y-%m-%d')
    stock_slug = stock.symbol.lower().replace("$", "").replace(".", "-")
    filename = f"_posts/{date_str}-{stock_slug}-analysis.md"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
    except Exception as e:
        logger.error(f"Failed to create blog post: {e}")
        return None
    
    logger.info(f"Blog post created: {filename}")
    return filename


# print_stock_info()
# get_company_url(sorted_day_gainers[0])

result = get_agent_analysis()
if result:
    post_file = create_blog_post(result)
    print(f"Blog post created: {post_file}")
    if post_file:
        # result["stock"] is already a StockData object
        stock_data = result["stock"]
        
        # Create or update database entry
        if not stock_exists(stock_data.symbol):
            create_stock_data(stock_data)
            logger.info(f"Database entry created for {stock_data.symbol}")
            update_reviewed_date(stock_data.symbol)
            logger.info(f"Marked {stock_data.symbol} as reviewed with current timestamp")
        else:
            update_reviewed_date(stock_data.symbol)
            logger.info(f"Stock {stock_data.symbol} already exists in database, updated last reviewed timestamp")
else:
    print("No unreviewed stocks to create blog post")
