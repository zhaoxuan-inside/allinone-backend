import asyncio
import json
from typing import Dict, Optional, Any
from kazoo.client import KazooClient, KazooState


class ConfigCenter:
    def __init__(self, hosts: str = "localhost:2181"):
        self.hosts = hosts
        self.client = None
        self._config_cache: Dict[str, Any] = {}
        self._watch_callbacks: Dict[str, list] = {}
        self._connected_event = asyncio.Event()

    async def init(self):
        self.client = KazooClient(hosts=self.hosts)
        
        def state_listener(state):
            if state == KazooState.CONNECTED:
                self._connected_event.set()
            elif state == KazooState.LOST:
                self._connected_event.clear()
            elif state == KazooState.SUSPENDED:
                pass
        
        self.client.add_listener(state_listener)
        self.client.start()
        await self._wait_for_connection()

    async def _wait_for_connection(self, timeout: int = 30):
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception("Failed to connect to ZooKeeper")

    async def get_config(self, key: str, default: Any = None) -> Any:
        path = f"/config/allinone/{key}"
        
        if key in self._config_cache:
            return self._config_cache[key]
        
        try:
            if self.client.exists(path):
                data, _ = self.client.get(path, watch=self._create_watch(key))
                value = self._parse_data(data)
                self._config_cache[key] = value
                return value
            return default
        except Exception as e:
            print(f"Error getting config {key}: {e}")
            return default

    async def set_config(self, key: str, value: Any):
        path = f"/config/allinone/{key}"
        data = self._serialize_data(value)
        
        try:
            if self.client.exists(path):
                self.client.set(path, data)
            else:
                self.client.create(path, data, makepath=True)
            
            self._config_cache[key] = value
            await self._notify_callbacks(key, value)
        except Exception as e:
            print(f"Error setting config {key}: {e}")

    async def get_all_configs(self) -> Dict[str, Any]:
        root_path = "/config/allinone"
        configs = {}
        
        try:
            if self.client.exists(root_path):
                children = self.client.get_children(root_path)
                for child in children:
                    path = f"{root_path}/{child}"
                    data, _ = self.client.get(path, watch=self._create_watch(child))
                    configs[child] = self._parse_data(data)
                    self._config_cache[child] = configs[child]
            return configs
        except Exception as e:
            print(f"Error getting all configs: {e}")
            return {}

    def register_callback(self, key: str, callback):
        if key not in self._watch_callbacks:
            self._watch_callbacks[key] = []
        self._watch_callbacks[key].append(callback)

    def _create_watch(self, key: str):
        def watch(event):
            asyncio.create_task(self._handle_watch(key))
        return watch

    async def _handle_watch(self, key: str):
        path = f"/config/allinone/{key}"
        try:
            if self.client.exists(path):
                data, _ = self.client.get(path, watch=self._create_watch(key))
                value = self._parse_data(data)
                old_value = self._config_cache.get(key)
                self._config_cache[key] = value
                await self._notify_callbacks(key, value, old_value)
        except Exception as e:
            print(f"Error handling watch for {key}: {e}")

    async def _notify_callbacks(self, key: str, new_value: Any, old_value: Any = None):
        callbacks = self._watch_callbacks.get(key, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(key, new_value, old_value)
                else:
                    callback(key, new_value, old_value)
            except Exception as e:
                print(f"Error in callback for {key}: {e}")

    def _serialize_data(self, value: Any) -> bytes:
        if isinstance(value, (dict, list)):
            return json.dumps(value).encode('utf-8')
        return str(value).encode('utf-8')

    def _parse_data(self, data: bytes) -> Any:
        try:
            return json.loads(data.decode('utf-8'))
        except json.JSONDecodeError:
            return data.decode('utf-8')

    async def close(self):
        if self.client:
            self.client.stop()
            self.client.close()


config_center: ConfigCenter = None


async def init_config_center(hosts: str = "localhost:2181"):
    global config_center
    config_center = ConfigCenter(hosts=hosts)
    await config_center.init()


async def get_config(key: str, default: Any = None) -> Any:
    if not config_center:
        return default
    return await config_center.get_config(key, default)


async def set_config(key: str, value: Any):
    if config_center:
        await config_center.set_config(key, value)


async def get_all_configs() -> Dict[str, Any]:
    if not config_center:
        return {}
    return await config_center.get_all_configs()