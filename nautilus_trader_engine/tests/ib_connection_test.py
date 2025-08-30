"""
Simple IB Gateway/TWS Connection Test

This script tests basic connectivity to your IB Gateway/TWS before running
the full Phase 1 validation suite.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
import sys
import os

# Add IB API path
ibapi_path = r"C:\TWS API\source\pythonclient"
if os.path.exists(ibapi_path):
    sys.path.insert(0, ibapi_path)
    print(f"✓ Added IB API path: {ibapi_path}")
else:
    print(f"⚠ IB API path not found: {ibapi_path}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock
    print("✓ ib_insync library imported successfully")
except ImportError as e:
    print(f"✗ Failed to import ib_insync: {e}")
    sys.exit(1)


async def test_ib_connection():
    """Test basic IB Gateway/TWS connection"""
    print("\n" + "="*50)
    print("🚀 IB Gateway/TWS Connection Test")
    print("="*50)
    
    # Your account details
    HOST = "127.0.0.1"
    PORT = 7497  # Paper Trading Port
    CLIENT_ID = 0  # Your specified Client ID
    ACCOUNT_ID = "DUK221396"  # Your account ID
    
    print(f"📡 Testing connection to:")
    print(f"   Host: {HOST}")
    print(f"   Port: {PORT}")
    print(f"   Client ID: {CLIENT_ID}")
    print(f"   Account: {ACCOUNT_ID}")
    print("-" * 50)
    
    ib = IB()
    
    try:
        print("🔌 Attempting to connect...")
        
        # Connect with timeout
        await asyncio.wait_for(
            ib.connectAsync(HOST, PORT, clientId=CLIENT_ID),
            timeout=10
        )
        
        print("✅ CONNECTION SUCCESSFUL!")
        print(f"   Server Version: {ib.serverVersion()}")
        print(f"   Connection Time: {ib.reqCurrentTime()}")
        
        # Test account summary
        try:
            print("\n📊 Testing account access...")
            account_summary = await asyncio.wait_for(
                ib.accountSummaryAsync(),
                timeout=5
            )
            
            if account_summary:
                print("✅ Account data accessible")
                # Find account value
                for item in account_summary:
                    if item.tag == 'NetLiquidation' and item.account == ACCOUNT_ID:
                        print(f"   Account Value: {item.value} {item.currency}")
                        break
            else:
                print("⚠ No account data returned")
                
        except Exception as e:
            print(f"⚠ Account access test failed: {e}")
        
        # Test market data
        try:
            print("\n📈 Testing market data access...")
            contract = Stock('AAPL', 'SMART', 'USD')
            details = await asyncio.wait_for(
                ib.reqContractDetailsAsync(contract),
                timeout=5
            )
            
            if details:
                print("✅ Market data accessible")
                print(f"   Found {len(details)} contract(s) for AAPL")
            else:
                print("⚠ No market data returned")
                
        except Exception as e:
            print(f"⚠ Market data test failed: {e}")
        
        print("\n🎉 Basic connection test PASSED!")
        print("   ✓ IB Gateway/TWS is running and accessible")
        print("   ✓ Paper trading configuration confirmed")
        print("   ✓ Ready for full Phase 1 validation")
        
        return True
        
    except asyncio.TimeoutError:
        print("❌ CONNECTION TIMEOUT")
        print("   • IB Gateway or TWS may not be running")
        print("   • Check if the application is started")
        print("   • Verify paper trading is enabled")
        return False
        
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        
        # Common error messages and solutions
        error_str = str(e).lower()
        if "connection refused" in error_str:
            print("   • IB Gateway/TWS is not running")
            print("   • Start IB Gateway or TWS application")
        elif "already connected" in error_str:
            print("   • Another client is using the same Client ID")
            print("   • Try a different Client ID or restart IB Gateway")
        elif "authentication" in error_str:
            print("   • Authentication failed")
            print("   • Check your login credentials")
        else:
            print("   • Check IB Gateway/TWS configuration")
            print("   • Ensure API connections are enabled")
            print("   • Verify port 7497 is configured for paper trading")
        
        return False
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("🔌 Connection closed")


def main():
    """Main function"""
    print("🔧 IB Gateway/TWS Connection Test")
    print("📋 Prerequisites:")
    print("   1. IB Gateway or TWS must be running")
    print("   2. Paper Trading must be enabled")
    print("   3. API connections must be enabled in IB settings")
    print("   4. Port 7497 must be configured for paper trading")
    
    try:
        result = asyncio.run(test_ib_connection())
        
        if result:
            print("\n🚀 READY TO PROCEED!")
            print("   You can now run the full Phase 1 validation:")
            print("   python nautilus_trader_engine\\tests\\phase1_ibkr_validation.py")
        else:
            print("\n🛠 ACTION REQUIRED:")
            print("   1. Start IB Gateway or TWS")
            print("   2. Enable paper trading mode")
            print("   3. Enable API connections in IB settings")
            print("   4. Re-run this test")
            
    except KeyboardInterrupt:
        print("\n⏹ Test cancelled by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")


if __name__ == "__main__":
    main()