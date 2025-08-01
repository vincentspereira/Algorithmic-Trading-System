"""
Nautilus Trader SDK Webhook Client

Webhook management client for the Nautilus Trader Python SDK.
"""

from typing import Dict, List, Optional, Any
from .exceptions import WebhookError

class WebhookClient:
    """Webhook management client"""
    
    def __init__(self, main_client):
        self.client = main_client
        self.base_url = f"{main_client.base_url}/api/v1/webhooks"
    
    async def create_webhook(
        self,
        url: str,
        events: List[str],
        name: str,
        secret: Optional[str] = None,
        security_type: str = "hmac_sha256",
        **kwargs
    ) -> str:
        """Create webhook endpoint"""
        data = {
            'url': url,
            'events': events,
            'name': name,
            'security_type': security_type,
            **kwargs
        }
        
        if secret:
            data['secret'] = secret
        
        try:
            async with self.client.session.post(
                self.base_url,
                json=data,
                headers=self.client._get_auth_headers()
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    return result['data']['id']
                else:
                    error_data = await response.json()
                    raise WebhookError(error_data.get('error', 'Failed to create webhook'))
        except Exception as e:
            if isinstance(e, WebhookError):
                raise
            raise WebhookError(f"Error creating webhook: {e}")
    
    async def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhook endpoints"""
        try:
            async with self.client.session.get(
                self.base_url,
                headers=self.client._get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data']
                else:
                    error_data = await response.json()
                    raise WebhookError(error_data.get('error', 'Failed to get webhooks'))
        except Exception as e:
            if isinstance(e, WebhookError):
                raise
            raise WebhookError(f"Error getting webhooks: {e}")
    
    async def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Get webhook endpoint by ID"""
        try:
            async with self.client.session.get(
                f"{self.base_url}/{webhook_id}",
                headers=self.client._get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data']
                else:
                    error_data = await response.json()
                    raise WebhookError(error_data.get('error', 'Webhook not found'))
        except Exception as e:
            if isinstance(e, WebhookError):
                raise
            raise WebhookError(f"Error getting webhook: {e}")
    
    async def update_webhook(
        self,
        webhook_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update webhook endpoint"""
        try:
            async with self.client.session.put(
                f"{self.base_url}/{webhook_id}",
                json=kwargs,
                headers=self.client._get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data']
                else:
                    error_data = await response.json()
                    raise WebhookError(error_data.get('error', 'Failed to update webhook'))
        except Exception as e:
            if isinstance(e, WebhookError):
                raise
            raise WebhookError(f"Error updating webhook: {e}")
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete webhook endpoint"""
        try:
            async with self.client.session.delete(
                f"{self.base_url}/{webhook_id}",
                headers=self.client._get_auth_headers()
            ) as response:
                return response.status == 200
        except Exception as e:
            raise WebhookError(f"Error deleting webhook: {e}")
    
    async def test_webhook(self, webhook_id: str, test_data: Optional[Dict] = None) -> bool:
        """Test webhook endpoint"""
        data = {'test_data': test_data} if test_data else {}
        
        try:
            async with self.client.session.post(
                f"{self.base_url}/{webhook_id}/test",
                json=data,
                headers=self.client._get_auth_headers()
            ) as response:
                return response.status == 200
        except Exception as e:
            raise WebhookError(f"Error testing webhook: {e}")
    
    async def get_webhook_stats(self, webhook_id: str) -> Dict[str, Any]:
        """Get webhook delivery statistics"""
        try:
            async with self.client.session.get(
                f"{self.base_url}/{webhook_id}/stats",
                headers=self.client._get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data']
                else:
                    error_data = await response.json()
                    raise WebhookError(error_data.get('error', 'Failed to get webhook stats'))
        except Exception as e:
            if isinstance(e, WebhookError):
                raise
            raise WebhookError(f"Error getting webhook stats: {e}")
    
    async def get_webhook_deliveries(
        self,
        webhook_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get webhook delivery history"""
        params = {'limit': limit}
        
        try:
            async with self.client.session.get(
                f"{self.base_url}/{webhook_id}/deliveries",
                params=params,
                headers=self.client._get_auth_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data']
                else:
                    error_data = await response.json()
                    raise WebhookError(error_data.get('error', 'Failed to get webhook deliveries'))
        except Exception as e:
            if isinstance(e, WebhookError):
                raise
            raise WebhookError(f"Error getting webhook deliveries: {e}")