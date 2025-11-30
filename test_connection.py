"""
Test script to verify Kraken API connection and configuration
"""
from kraken_client import KrakenClient
from config import Config

def test_connection():
    """Test Kraken API connection"""
    print("🧪 Testing Kraken API Connection")
    print("=" * 60)

    try:
        # Validate config
        print("1️⃣ Validating configuration...")
        Config.validate()
        print("   ✅ Configuration valid")

    except ValueError as e:
        print(f"   ❌ Configuration error: {e}")
        print("\n📝 Please edit .env file and configure your API credentials")
        return False

    try:
        # Initialize client
        print("\n2️⃣ Initializing Kraken client...")
        client = KrakenClient()
        print("   ✅ Client initialized")

        # Test public API - get ticker
        print("\n3️⃣ Testing public API (get ticker)...")
        ticker = client.get_ticker(Config.TRADING_PAIR)

        if ticker:
            print("   ✅ Public API working")
            print(f"   📊 BTC/USD Price: ${ticker['last']:,.2f}")
            print(f"   📊 24h High: ${ticker['high']:,.2f}")
            print(f"   📊 24h Low: ${ticker['low']:,.2f}")
        else:
            print("   ❌ Failed to get ticker")
            return False

        # Test private API - get balance
        print("\n4️⃣ Testing private API (get balance)...")
        balance = client.get_account_balance()

        if balance:
            print("   ✅ Private API working")
            print("   💰 Account Balance:")
            for currency, amount in balance.items():
                if amount > 0:
                    print(f"      {currency}: {amount:.6f}")
        else:
            print("   ❌ Failed to get balance")
            print("   ⚠️  Check your API credentials and permissions")
            return False

        # Test getting OHLC data
        print("\n5️⃣ Testing market data (OHLC)...")
        df = client.get_ohlc_data(Config.TRADING_PAIR, interval=60)

        if df is not None and len(df) > 0:
            print("   ✅ OHLC data retrieved")
            print(f"   📊 Retrieved {len(df)} candles")
            print(f"   📊 Latest close: ${df.iloc[-1]['close']:,.2f}")
        else:
            print("   ❌ Failed to get OHLC data")
            return False

        print("\n" + "=" * 60)
        print("✅ All tests passed! Bot is ready to run.")
        print("\n🚀 To start the bot, run:")
        print("   python bot.py")
        print("   # or")
        print("   ./start.sh")
        print("\n⚠️  REMEMBER:")
        print("   - Start with small amounts to test")
        print("   - Monitor the bot closely")
        print("   - Trading involves risk of loss")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        return False


if __name__ == "__main__":
    test_connection()
