import asyncio
import random
from typing import List, Optional, Dict

try:
    from v2.nacos.naming.nacos_naming_service import NacosNamingService
    from v2.nacos.common.client_config import ClientConfig
    from v2.nacos.naming.model.naming_param import ListInstanceParam
    NEW_API = True
except ImportError:
    try:
        from nacos import NacosClient
        NEW_API = False
    except ImportError:
        from nacos.client import NacosClient
        NEW_API = False


class ServiceInstance:
    def __init__(self, ip: str, port: int, weight: float = 1.0, healthy: bool = True):
        self.ip = ip
        self.port = port
        self.weight = weight
        self.healthy = healthy

    def get_url(self) -> str:
        return f"http://{self.ip}:{self.port}"

    def __repr__(self):
        return f"ServiceInstance(ip={self.ip}, port={self.port}, weight={self.weight}, healthy={self.healthy})"


class LoadBalancer:
    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        healthy_instances = [i for i in instances if i.healthy]
        if not healthy_instances:
            return None
        return self._select(healthy_instances)

    def _select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        raise NotImplementedError


class RoundRobinBalancer(LoadBalancer):
    def __init__(self):
        self.index = 0

    def _select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        instance = instances[self.index % len(instances)]
        self.index += 1
        return instance


class RandomBalancer(LoadBalancer):
    def _select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        return random.choice(instances)


class WeightedRandomBalancer(LoadBalancer):
    def _select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        total_weight = sum(i.weight for i in instances)
        if total_weight == 0:
            return random.choice(instances)
        
        random_weight = random.uniform(0, total_weight)
        current_weight = 0
        for instance in instances:
            current_weight += instance.weight
            if current_weight >= random_weight:
                return instance
        return instances[-1]


class NacosServiceDiscovery:
    def __init__(self, server_addresses: str, namespace: str = "public", username: str = None, password: str = None):
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.username = username
        self.password = password
        self.client = None
        self._instance_cache: Dict[str, List[ServiceInstance]] = {}
        self._update_interval = 30

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
        asyncio.create_task(self._periodic_update())

    async def _periodic_update(self):
        while True:
            await self.update_all_services()
            await asyncio.sleep(self._update_interval)

    async def update_all_services(self):
        if NEW_API:
            pass
        else:
            services = await self.client.list_naming_services()
            for service_name in services:
                await self.update_service(service_name)

    async def update_service(self, service_name: str):
        try:
            if NEW_API:
                request = ListInstanceParam(
                    service_name=service_name,
                    subscribe=True,
                    healthy_only=True
                )
                instances = await self.client.list_instances(request)
                service_instances = []
                for instance in instances:
                    service_instances.append(ServiceInstance(
                        ip=instance.ip,
                        port=instance.port,
                        weight=instance.weight,
                        healthy=instance.healthy
                    ))
                self._instance_cache[service_name] = service_instances
            else:
                result = await self.client.list_naming_instances(service_name)
                instances = []
                for instance in result.get("hosts", []):
                    instances.append(ServiceInstance(
                        ip=instance.get("ip"),
                        port=instance.get("port"),
                        weight=instance.get("weight", 1.0),
                        healthy=instance.get("healthy", False)
                    ))
                self._instance_cache[service_name] = instances
        except Exception as e:
            print(f"Failed to update service {service_name}: {e}")

    async def get_instances(self, service_name: str) -> List[ServiceInstance]:
        if service_name not in self._instance_cache:
            await self.update_service(service_name)
        return self._instance_cache.get(service_name, [])

    async def get_instance(self, service_name: str, balancer: LoadBalancer) -> Optional[ServiceInstance]:
        instances = await self.get_instances(service_name)
        return balancer.select(instances)

    async def close(self):
        if self.client:
            await self.client.shutdown()