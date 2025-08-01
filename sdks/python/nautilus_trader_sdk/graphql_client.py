"""
Nautilus Trader SDK GraphQL Client

GraphQL client for the Nautilus Trader Python SDK.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
import aiohttp

from .exceptions import GraphQLError, NetworkError

class GraphQLClient:
    """GraphQL client for Nautilus Trader"""
    
    def __init__(self, main_client):
        self.client = main_client
        self.graphql_url = f"{main_client.base_url}/graphql"
    
    async def query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        return await self._execute(query, variables)
    
    async def mutation(self, mutation: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL mutation"""
        return await self._execute(mutation, variables)
    
    async def subscription(
        self,
        subscription: str,
        callback: Callable[[Dict], None],
        variables: Optional[Dict] = None
    ):
        """Subscribe to GraphQL subscription"""
        # In a real implementation, this would use WebSocket subscriptions
        # For now, we'll simulate with polling
        while True:
            try:
                result = await self._execute(subscription, variables)
                if result.get('data'):
                    callback(result['data'])
                await asyncio.sleep(1)  # Poll every second
            except Exception as e:
                self.client.logger.error(f"GraphQL subscription error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _execute(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL operation"""
        await self.client.connect()
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            async with self.client.session.post(
                self.graphql_url,
                json=payload,
                headers=self.client._get_auth_headers()
            ) as response:
                result = await response.json()
                
                if result.get('errors'):
                    raise GraphQLError(
                        "GraphQL query failed",
                        errors=result['errors']
                    )
                
                return result
                
        except aiohttp.ClientError as e:
            raise NetworkError(f"GraphQL network error: {e}")
    
    # Convenience methods for common queries
    async def get_orders(self, limit: int = 10) -> Dict[str, Any]:
        """Get orders using GraphQL"""
        query = """
        query GetOrders($limit: Int) {
            orders(limit: $limit) {
                id
                symbol
                side
                quantity
                price
                status
                createdAt
            }
        }
        """
        return await self.query(query, {'limit': limit})
    
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get portfolio using GraphQL"""
        query = """
        query GetPortfolio {
            portfolio {
                totalValue
                cashBalance
                totalPnl
                dailyPnl
                positions {
                    symbol
                    quantity
                    marketValue
                    unrealizedPnl
                }
            }
        }
        """
        return await self.query(query)
    
    async def create_order_mutation(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create order using GraphQL mutation"""
        mutation = """
        mutation CreateOrder($symbol: String!, $side: String!, $quantity: Float!, $orderType: String!, $price: Float) {
            createOrder(symbol: $symbol, side: $side, quantity: $quantity, orderType: $orderType, price: $price) {
                success
                message
                order {
                    id
                    symbol
                    side
                    quantity
                    price
                    status
                }
            }
        }
        """
        variables = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'orderType': order_type
        }
        if price is not None:
            variables['price'] = price
        
        return await self.mutation(mutation, variables)