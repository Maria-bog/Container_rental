from sqlalchemy import Column, Integer, String, DateTime, Float
from database import Base
import datetime

class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, index=True)
    instance_type = Column(String)
    os = Column(String)
    cpu = Column(Integer)
    ram = Column(Integer)
    disk = Column(Integer)  
    owner = Column(String)
    status = Column(String) 
    
    ssh_host = Column(String, default="localhost")
    ssh_port = Column(Integer)
    
    container_id = Column(String, nullable=True)  # ID контейнера от Docker
    pid = Column(Integer, nullable=True)  # PID процесса QEMU (для vms)
    
    max_runtime = Column(Integer, default=60)  # в минутах
    network_limit = Column(Integer, default=500)  # в MB
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    total_cpu_time = Column(Float, default=0.0)
    total_network_rx = Column(Integer, default=0)

class Metric(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    cpu_usage_percent = Column(Float)
    memory_usage_mb = Column(Float)
    network_rx_bytes = Column(Integer)
    network_tx_bytes = Column(Integer)
