from nacos import NacosClient
import socket


class NacosServiceRegistry:
    def __init__(self, server_addresses: str, namespace: str = "public"):
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.client = None

    async def init(self):
        self.client = NacosClient(
            server_addresses=self.server_addresses,
            namespace=self.namespace,
            async_req=True
        )
        await self.client.init()

    async def register_service(self, service_name: str, ip: str = None, port: int = 8000):
        if not ip:
            ip = self._get_local_ip()
        
        await self.client.register_instance(
            service_name=service_name,
            ip=ip,
            port=port,
            metadata={"version": "1.0"}
        )

    async def deregister_service(self, service_name: str, ip: str = None, port: int = 8000):
        if not ip:
            ip = self._get_local_ip()
        
        await self.client.deregister_instance(
            service_name=service_name,
            ip=ip,
            port=port
        )

    def _get_local_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    async def close(self):
        if self.client:
            await self.client.shutdown()