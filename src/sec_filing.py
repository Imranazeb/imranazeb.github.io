import yfinance as yf


def get_recent_sec_filings(symbol: str, filing_type: str = "8-K", limit: int = 5):
    """Get recent SEC filings for a stock symbol"""
    ticker = yf.Ticker(symbol)
    filings = ticker.sec_filings

    # Filter by filing type
    filtered = [f for f in filings if f["type"] == filing_type][:limit]

    return [
        {
            "type": f["type"],
            "date": f["date"],
            "title": f["title"],
            "url": f["edgarUrl"],
        }
        for f in filtered
    ]


def get_8K_filings(symbol):
    recent_8k = get_recent_sec_filings(symbol, "8-K", 1)

    if recent_8k:
        print(f"\nRecent SEC Filings (8-K) for {symbol}:\n")
        for filing in recent_8k:
            # print(f"- {filing['date']}: {filing['title']}")
            return {"title": filing["title"], "url": filing["url"]}
    else:
        print(f"No recent 8-K filings found for {symbol}.")
        return None
