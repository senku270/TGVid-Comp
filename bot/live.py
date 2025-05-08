from aiohttp import web

async def health_check(request):
    return web.Response(text="OK")

class HealthServer:
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.health_app = None
        self.runner = None

    async def start(self):
        """Start the health check server"""
        try:
            self.health_app = web.Application()
            self.health_app.router.add_get('/health', health_check)

            self.runner = web.AppRunner(self.health_app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, self.host, self.port)
            await site.start()
            print(f"Health check server started on port {self.port}")
        except Exception as e:
            print(f"Failed to start health server: {e}")

    async def stop(self):
        """Stop the health check server"""
        if self.runner:
            await self.runner.cleanup()