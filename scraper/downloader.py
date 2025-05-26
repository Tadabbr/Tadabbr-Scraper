import asyncio
import aiohttp
import argparse
from pathlib import Path


async def fetch(session, page: int, tafsir_number: int, download_dir: Path):
    """Fetch a URL and save its content to a file if valid."""
    url = f"https://www.islamweb.org/ar/library/content/{tafsir_number}/{page}"
    try:
        async with session.get(url) as response:
            text = await response.text()            
            # Save content to file
            file_path = download_dir / f"page_{page}.html"
            file_path.write_text(text, encoding='utf-8')
            return text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


async def fetch_all(start: int, end: int, tafsir_number: int, download_dir: Path) -> list[str]:
    """Fetch multiple URLs concurrently and save results to files."""
    pages = range(start, end + 1)
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        tasks = [fetch(session, page, tafsir_number, download_dir) for page in pages]
        html_pages = await asyncio.gather(*tasks)
    
    return [html for html in html_pages if html]


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Async web scraper for Islamic library content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start 1 --end 10 --tafsir 123 --downloads ./html
  %(prog)s -s 50 -e 74 -t 456 -d ./content
  %(prog)s --help
        """
    )
    
    parser.add_argument(
        '--start', '-s',
        type=int,
        default=1,
        help='Starting page number (default: 1)'
    )
    
    parser.add_argument(
        '--end', '-e',
        type=int,
        required=True,
        help='Ending page number (inclusive, required)'
    )
    
    parser.add_argument(
        '--tafsir', '-t',
        type=int,
        required=True,
        help='Tafsir number for the URL (required)'
    )
    
    parser.add_argument(
        '--downloads', '-d',
        type=str,
        required=True,
        help='Directory to save downloaded HTML files (required)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def main():
    """Main function to run the async fetcher."""
    args = parse_arguments()
    
    if args.end < args.start:
        raise ValueError("End page must be greater than or equal to start page")
    
    # Create downloads directory
    download_dir = Path(args.downloads)
    download_dir.mkdir(parents=True, exist_ok=True)
    
    if args.verbose:
        print(f"Starting fetch with parameters:")
        print(f"  Start: {args.start}")
        print(f"  End: {args.end}")
        print(f"  Tafsir Number: {args.tafsir}")
        print(f"  Save Location: {download_dir.resolve()}")
        print()
    
    # Run the async function
    html_pages = asyncio.run(fetch_all(args.start, args.end, args.tafsir, download_dir))
    
    if args.verbose:
        print(f"\nSuccessfully fetched {len(html_pages)} pages")
        print(f"Saved files to: {download_dir.resolve()}")
        print("\nFile sizes:")
        for page in range(args.start, args.end + 1):
            file_path = download_dir / f"page_{page}.html"
            if file_path.exists():
                print(f"  {file_path.name}: {file_path.stat().st_size} bytes")
            else:
                print(f"  {file_path.name}: [missing]")
        print()


if __name__ == "__main__":
    main() 