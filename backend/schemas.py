from pydantic import BaseModel
from typing import Optional
from datetime import datetime
class InstanceCreate(BaseModel):
    type: str 
    os: str
    cpu: int
    ram: int
    disk: int
    owner: str
    max_runtime: int
    network_limit: int


class InstanceResponse(BaseModel):
    id: int
    instance_type: str
    os: str
    status: str
    cpu: int
    ram: int
    disk: int
    owner: str
    ssh_host: str
    ssh_port: int
    max_runtime: int
    network_limit: int
    created_at: datetime
    image_path: Optional[str] = None
    
    class Config:
        orm_mode = True 


class StatsResponse(BaseModel):
    cpu_usage_percent: float
    memory_usage_mb: float
    network_rx_bytes: int
    network_tx_bytes: int
    total_cpu_time_sec: float
    total_network_rx_mb: float
