"""
Run Kraken Scalp Bot with Web Dashboard

This script starts the bot with a web interface on http://localhost:8080
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.bot import KrakenScalpBot
from src.web.api import WebAPI


async def main():
    """Main entry point"""
    print("="*60)
    print("Kraken Scalp Bot - Web Dashboard")
    print("="*60)
    print("Starting bot with web interface...")
    print("Dashboard will be available at: http://localhost:8080")
    print("="*60)

    # Create bot
    bot = KrakenScalpBot(config_path="config/config.yaml")

    # Create web API
    web_api = WebAPI(bot)

    # Start web server
    try:
        await web_api.run(host="0.0.0.0", port=8080)
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        if bot.running:
            bot.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
