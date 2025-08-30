#!/usr/bin/env python3
"""
Test script for Multi-Source Data Feeds with Fallback Mechanism
Phase 1 - Core System Validation & Hardening
"""

import asyncio
import sys
import os
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.data_feeds.multi_source_feed_manager import DataFeedManager, DataSource

async def test_multi_source_feeds():
    """Test the multi-source data feed manager with fallback mechanisms"""
    
    print('🚀 Testing Multi-Source Data Feeds with Fallback Mechanism')
    print('=' * 60)
    print(f'Test Start Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    manager = DataFeedManager()
    test_results = {
        'test_start': datetime.now().isoformat(),
        'symbol_tests': {},
        'source_health': {},
        'statistics': {},
        'summary': {}
    }
    
    # Test symbols across different asset classes
    test_symbols = ['AAPL', 'MSFT', 'SPY', 'QQQ', 'EURUSD']
    
    total_tests = 0
    successful_tests = 0
    
    for symbol in test_symbols:
        print(f'\n📊 Testing {symbol}:')
        symbol_results = {
            'ibkr': None,
            'yahoo': None,
            'alpha_vantage': None,
            'automatic_fallback': None
        }
        
        # Test 1: Automatic source selection (primary IBKR with fallback)
        try:
            data = await manager.get_market_data(symbol)
            total_tests += 1
            if data and data.price > 0:
                successful_tests += 1
                print(f'  ✅ Automatic ({data.source}): Price: ${data.price:.4f} | Volume: {data.volume:,}')
                symbol_results['automatic_fallback'] = {
                    'status': 'SUCCESS',
                    'source': data.source,
                    'price': data.price,
                    'volume': data.volume
                }
            else:
                print(f'  ❌ Automatic: Failed to get data')
                symbol_results['automatic_fallback'] = {'status': 'FAILED'}
        except Exception as e:
            print(f'  ❌ Automatic: Error - {str(e)[:100]}')
            symbol_results['automatic_fallback'] = {'status': 'ERROR', 'error': str(e)}
        
        # Test 2: Force Yahoo Finance
        try:
            data = await manager.get_market_data(symbol, force_source=DataSource.YAHOO)
            total_tests += 1
            if data and data.price > 0:
                successful_tests += 1
                print(f'  ✅ Yahoo Finance: Price: ${data.price:.4f} | Volume: {data.volume:,}')
                symbol_results['yahoo'] = {
                    'status': 'SUCCESS',
                    'price': data.price,
                    'volume': data.volume
                }
            else:
                print(f'  ❌ Yahoo Finance: Failed to get data')
                symbol_results['yahoo'] = {'status': 'FAILED'}
        except Exception as e:
            print(f'  ⚠️  Yahoo Finance: Error - {str(e)[:100]}')
            symbol_results['yahoo'] = {'status': 'ERROR', 'error': str(e)}
        
        # Test 3: Force IBKR (if available)
        try:
            data = await manager.get_market_data(symbol, force_source=DataSource.IBKR)
            total_tests += 1
            if data and data.price > 0:
                successful_tests += 1
                print(f'  ✅ IBKR: Price: ${data.price:.4f} | Volume: {data.volume:,}')
                symbol_results['ibkr'] = {
                    'status': 'SUCCESS',
                    'price': data.price,
                    'volume': data.volume
                }
            else:
                print(f'  ⚠️  IBKR: No data available (connection may be inactive)')
                symbol_results['ibkr'] = {'status': 'NO_DATA'}
        except Exception as e:
            print(f'  ⚠️  IBKR: Error - {str(e)[:100]}')
            symbol_results['ibkr'] = {'status': 'ERROR', 'error': str(e)}
        
        # Test 4: Force Alpha Vantage (usually requires API key)
        try:
            data = await manager.get_market_data(symbol, force_source=DataSource.ALPHA_VANTAGE)
            total_tests += 1
            if data and data.price > 0:
                successful_tests += 1
                print(f'  ✅ Alpha Vantage: Price: ${data.price:.4f}')
                symbol_results['alpha_vantage'] = {
                    'status': 'SUCCESS',
                    'price': data.price
                }
            else:
                print(f'  ⚠️  Alpha Vantage: No API key or rate limited')
                symbol_results['alpha_vantage'] = {'status': 'NO_API_KEY'}
        except Exception as e:
            print(f'  ⚠️  Alpha Vantage: Error - {str(e)[:100]}')
            symbol_results['alpha_vantage'] = {'status': 'ERROR', 'error': str(e)}
        
        test_results['symbol_tests'][symbol] = symbol_results
    
    # Test health monitoring
    print(f'\n📈 Data Source Health Status:')
    for source, health in manager.health_monitor.items():
        status = health['status']
        success_rate = health['success_rate']
        total_requests = health['total_requests']
        
        print(f'  {source}: {status} (Success Rate: {success_rate:.1%}, Requests: {total_requests})')
        test_results['source_health'][source] = {
            'status': status,
            'success_rate': success_rate,
            'total_requests': total_requests,
            'successes': health['successes']
        }
    
    # Test statistics
    print(f'\n📊 Feed Statistics:')
    stats = manager.get_statistics()
    for source, stat in stats.items():
        requests = stat['requests']
        successes = stat['successes']
        success_rate = (successes / requests * 100) if requests > 0 else 0
        
        print(f'  {source}: {requests} requests, {successes} successes ({success_rate:.1f}%)')
        test_results['statistics'][source] = {
            'requests': requests,
            'successes': successes,
            'success_rate': success_rate
        }
    
    # Summary
    overall_success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    print(f'\n🎯 Test Summary:')
    print(f'  Total Tests: {total_tests}')
    print(f'  Successful Tests: {successful_tests}')
    print(f'  Overall Success Rate: {overall_success_rate:.1f}%')
    print(f'  Multi-Source Feeds: {"✅ OPERATIONAL" if overall_success_rate >= 70 else "❌ NEEDS ATTENTION"}')
    
    test_results['summary'] = {
        'total_tests': total_tests,
        'successful_tests': successful_tests,
        'success_rate': overall_success_rate,
        'status': 'OPERATIONAL' if overall_success_rate >= 70 else 'NEEDS_ATTENTION',
        'test_end': datetime.now().isoformat()
    }
    
    # Save test results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'multi_source_feeds_test_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f'\n💾 Test results saved to: {results_file}')
    
    return test_results

if __name__ == '__main__':
    asyncio.run(test_multi_source_feeds())