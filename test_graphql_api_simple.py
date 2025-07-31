#!/usr/bin/env python3
"""
Simple test for GraphQL API functionality
"""

def test_graphql_api():
    """Test GraphQL API creation and basic functionality"""
    try:
        from nautilus_trader_engine.api.graphql_api import create_graphql_api, GRAPHQL_AVAILABLE
        
        print(f"GraphQL Available: {GRAPHQL_AVAILABLE}")
        
        if not GRAPHQL_AVAILABLE:
            print("❌ GraphQL not available")
            return False
        
        # Create API instance
        api = create_graphql_api()
        print("✓ GraphQL API created successfully")
        
        # Test schema creation
        schema = api.schema
        print("✓ GraphQL schema accessible")
        
        # Test simple query
        result = schema.execute('{ __schema { types { name } } }')
        if result.errors:
            print(f"❌ Query errors: {result.errors}")
            return False
        
        print("✓ Schema introspection query successful")
        print(f"✓ Found {len(result.data['__schema']['types'])} types in schema")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_graphql_api()
    if success:
        print("\n🎉 GraphQL API is working correctly!")
    else:
        print("\n❌ GraphQL API has issues")