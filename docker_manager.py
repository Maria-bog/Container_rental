import docker
import random
import time
from docker.types import RestartPolicy

client = docker.from_env()


SSH_PORT_RANGE = range(2200, 2300)

def find_free_port():
    """Находит свободный порт на хосте."""
    for port in SSH_PORT_RANGE:
        try:
            
            containers = client.containers.list(filters={"publish": f"{port}/tcp"})
            if not containers:
                return port
        except:
            return port
    raise Exception("No free ports available")

def create_container(cpu: int, ram_mb: int, os_image: str, ssh_password: str = "password"):
    """
    Создает и запускает Docker-контейнер с SSH сервером.
    Возвращает container_id и проброшенный порт.
    """
    
    host_port = find_free_port()
    
    
    ram_bytes = ram_mb * 1024 * 1024
    
    
    environment = {
        "PUID": "1000",
        "PGID": "1000",
        "TZ": "Europe/Moscow",
        "USER_NAME": "user",
        "PASSWORD": ssh_password,
    }
    
    
    container = client.containers.run(
    image=os_image,
    detach=True,
    ports={'22/tcp': host_port},
    nano_cpus=int(cpu * 1e9),
    mem_limit=ram_bytes,
    environment=environment,
    command="sleep infinity",
    tty=True,
    stdin_open=True,
)
    
    
    time.sleep(3)
    
    return container.id, host_port

def stop_container(container_id):
    """Останавливает контейнер."""
    try:
        container = client.containers.get(container_id)
        container.stop()
        return True
    except docker.errors.NotFound:
        print(f"Container {container_id} not found")
        return False

def delete_container(container_id):
    """Останавливает и удаляет контейнер."""
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        return True
    except docker.errors.NotFound:
        print(f"Container {container_id} not found")
        return False

def get_container_stats(container_id):
    """Получает статистику использования ресурсов контейнера."""
    try:
        container = client.containers.get(container_id)
        stats = container.stats(stream=False)
        
       
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        num_cpus = stats['cpu_stats']['online_cpus']
        
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
        
        
        memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)
        
        
        network_rx = 0
        network_tx = 0
        if 'networks' in stats:
            for iface, data in stats['networks'].items():
                network_rx += data['rx_bytes']
                network_tx += data['tx_bytes']
        
        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(memory_usage, 2),
            "network_rx_bytes": network_rx,
            "network_tx_bytes": network_tx
        }
    except Exception as e:
        print(f"Error getting stats for container {container_id}: {e}")
        return None
