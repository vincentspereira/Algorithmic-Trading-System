#!/usr/bin/env python3
"""
Simple GraphQL test to verify dependencies are working
"""

def test_graphql_imports():
    """Test GraphQL imports"""
    try:
        import graphene
        print("✓ graphene imported successfully")
        
        from graphene import ObjectType, String, Schema
        print("✓ graphene types imported successfully")
        
        # Try to create a simple schema
        class Query(ObjectType):
            hello = String()
            
            def resolve_hello(self, info):
                return "Hello World!"
        
        schema = Schema(query=Query)
        print("✓ GraphQL schema created successfully")
        
        # Test query execution
        result = schema.execute('{ hello }')
        print(f"✓ Query executed successfully: {result.data}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_graphql_imports()
    if success:
        print("\n🎉 GraphQL is working correctly!")
    else:
        print("\n❌ GraphQL setup has issues")