    async def start_health_server(self):
        """Start the health check server"""
        try:
            self.health_app = web.Application()
            self.health_app.router.add_get('/health', health_check)

            self.runner = web.AppRunner(self.health_app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, "0.0.0.0", 8080)
            await site.start()
            print("Health check server started on port 8080")
        except Exception as e:
            print(f"Failed to start health server: {e}")

    async def stop_health_server(self):
        """Stop the health check server"""
        if self.runner:
            await self.runner.cleanup()

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        self.uptime = Config.BOT_UPTIME

        # Start health check server regardless of webhook config
        await self.start_health_server()