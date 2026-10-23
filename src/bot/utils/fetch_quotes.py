import asyncio
import logging
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.parent))
from src.bot.services.quote_scraper import QuoteScraper

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = QuoteScraper(
        output_path=pathlib.Path(__file__).parent.parent.parent.parent
        / "src"
        / "assets"
        / "data"
        / "quotes"
        / "quotes.json",
    )
    quotes = asyncio.run(scraper.run())
    print(f"Записано {len(quotes)} цитат: {scraper.output_path}")
