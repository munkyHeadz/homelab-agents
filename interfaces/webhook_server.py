"""
Webhook Server for Alertmanager Integration

Runs alongside the Telegram bot to receive Alertmanager webhooks.
"""

import asyncio
import json
from aiohttp import web
from typing import Callable, Optional

from shared.logging import get_logger
from shared.alert_manager import get_alert_manager

logger = get_logger(__name__)


class WebhookServer:
    """HTTP server for receiving webhooks"""
    
    def __init__(self, port: int = 8001, alert_callback: Optional[Callable] = None):
        self.port = port
        self.alert_callback = alert_callback
        self.alert_manager = get_alert_manager()
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Register routes
        self.app.router.add_post('/webhook/alerts', self.handle_alert_webhook)
        self.app.router.add_get('/health', self.health_check)
        
        logger.info("Webhook server initialized", port=port)
    
    async def handle_alert_webhook(self, request: web.Request) -> web.Response:
        """Handle Alertmanager webhook"""
        try:
            # Parse webhook payload
            payload = await request.json()
            
            logger.info("Received Alertmanager webhook",
                       alerts_count=len(payload.get('alerts', [])),
                       status=payload.get('status', 'unknown'))
            
            # Process alerts
            alerts = await self.alert_manager.process_webhook(payload)
            
            # Trigger callback for each new/updated alert
            if self.alert_callback:
                for alert in alerts:
                    try:
                        await self.alert_callback(alert)
                    except Exception as e:
                        logger.error("Alert callback failed", error=str(e))
            
            return web.json_response({
                'status': 'success',
                'alerts_processed': len(alerts)
            })
            
        except Exception as e:
            logger.error("Error processing webhook", error=str(e))
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        stats = self.alert_manager.get_stats()
        return web.json_response({
            'status': 'healthy',
            'alert_stats': stats
        })
    
    async def start(self):
        """Start the webhook server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        logger.info("Webhook server started", port=self.port)
    
    async def stop(self):
        """Stop the webhook server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Webhook server stopped")
