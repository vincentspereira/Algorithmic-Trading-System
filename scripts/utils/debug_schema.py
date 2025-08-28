#!/usr/bin/env python3
"""
This script is used to debug the GraphQL schema.

It creates a GraphQL API, prints the schema type and attributes,
and executes a simple query to test the schema.
"""

from nautilus_trader_engine.api.graphql_api import create_graphql_api

api = create_graphql_api()
schema = api.schema

print("Schema type:", type(schema))
print("Schema attributes:", [attr for attr in dir(schema) if not attr.startswith('_')])

# Test simple query
result = schema.execute('{ __schema { types { name } } }')
print("Query result errors:", result.errors)
print("Query result data keys:", list(result.data.keys()) if result.data else None)