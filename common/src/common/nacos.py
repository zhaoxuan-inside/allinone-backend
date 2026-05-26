import socket

try:
    from v2.nacos.naming.nacos_naming_service import NacosNamingService
    from v2.nacos.common.client_config import ClientConfig
    from v2.nacos.naming.model.naming_param import RegisterInstanceParam, DeregisterInstanceParam, ListInstanceParam
    NEW_API = True
except ImportError:
    try:
        from nacos import NacosClient
        NEW_API = False
    except ImportError:
        from nacos.client import NacosClient
        NEW_API = False


class NacosServiceRegistry:
    def __init__(self, server_addresses: str, namespace: str = "public", username: str = None, password: str = None):
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.username = username
        self.password = password
        self.client = None

    async def init(self):
        if NEW_API:
            client_config = ClientConfig(
                server_addresses=self.server_addresses,
                namespace_id=self.namespace,
                username=self.username,
                password=self.password
            )
            self.client = await NacosNamingService.create_naming_service(client_config)

        else:
            client_args = {
                "server_addresses": self.server_addresses,
                "namespace": self.namespace,
                "async_req": True
            }
            
            if self.username and self.password:
                client_args["username"] = self.username
                client_args["password"] = self.password
            
            self.client = NacosClient(**client_args)
            await self.client.init()

    async def register_service(self, service_name: str, ip: str = None, port: int = 8000):
        if not ip:
            ip = self._get_local_ip()
        
        if NEW_API:
            request = RegisterInstanceParam(
                service_name=service_name,
                ip=ip,
                port=port,
                metadata={"version": "1.0"}
            )
            await self.client.register_instance(request)
        else:
            await self.client.register_instance(
                service_name=service_name,
                ip=ip,
                port=port,
                metadata={"version": "1.0"}
            )

    async def deregister_service(self, service_name: str, ip: str = None, port: int = 8000):
        if not ip:
            ip = self._get_local_ip()
        
        if NEW_API:
            request = DeregisterInstanceParam(
                service_name=service_name,
                ip=ip,
                port=port
            )
            await self.client.deregister_instance(request)
        else:
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