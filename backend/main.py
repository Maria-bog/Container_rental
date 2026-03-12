from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import psutil
import threading
import time
import datetime

import models
import schemas
import docker_manager
import qemu_manager

from database import SessionLocal, engine


models.Base.metadata.create_all(bind=engine)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def monitor_instances():
    while True:
        db = SessionLocal()
        try:
            running_vms = db.query(models.Instance).filter(
                models.Instance.instance_type == "vm",
                models.Instance.status == "running"
            ).all()

            now = datetime.datetime.utcnow()

            for vm in running_vms:
                lifetime_minutes = (now - vm.created_at).total_seconds() / 60

                if vm.max_runtime and lifetime_minutes >= vm.max_runtime:
                    qemu_manager.stop_vm(vm.pid)
                    vm.status = "expired"

            db.commit()
        except Exception as e:
            print(f"Monitor error: {e}")
        finally:
            db.close()

        time.sleep(30)


@app.on_event("startup")
def start_monitor():
    thread = threading.Thread(target=monitor_instances, daemon=True)
    thread.start()


@app.post("/api/instances/create", response_model=schemas.InstanceResponse)
async def create_instance(instance: schemas.InstanceCreate, db: Session = Depends(get_db)):
    """
    Создает новый инстанс (VM или Container).
    """
    ssh_port = None
    container_id = None
    pid = None
    image_path = None

    if instance.type == "container":
        try:
            container_id, ssh_port = docker_manager.create_container(
                cpu=instance.cpu,
                ram_mb=instance.ram,
                os_image=instance.os,
                ssh_password="userpass"
            )
            status = "running"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create container: {str(e)}")

    elif instance.type == "vm":
        try:
            vm_data = qemu_manager.create_vm(
                disk_gb=instance.disk,
                ram_mb=instance.ram,
                cpu=instance.cpu
            )
            ssh_port = vm_data["ssh_port"]
            pid = vm_data["pid"]
            image_path = vm_data["image_path"]
            status = "running"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create VM: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail="Invalid instance type")

    db_instance = models.Instance(
        instance_type=instance.type,
        os=instance.os,
        cpu=instance.cpu,
        ram=instance.ram,
        disk=instance.disk,
        owner=instance.owner,
        status=status,
        ssh_host="localhost",
        ssh_port=ssh_port,
        container_id=container_id,
        pid=pid,
        image_path=image_path,
        max_runtime=instance.max_runtime,
        network_limit=instance.network_limit
    )
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)

    return db_instance


@app.get("/api/instances", response_model=List[schemas.InstanceResponse])
async def read_instances(db: Session = Depends(get_db)):
    """Возвращает список всех инстансов."""
    instances = db.query(models.Instance).all()
    return instances


@app.post("/api/instances/{instance_id}/stop")
async def stop_instance(instance_id: int, db: Session = Depends(get_db)):
    """Останавливает инстанс."""
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not db_instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    if db_instance.instance_type == "container" and db_instance.container_id:
        success = docker_manager.stop_container(db_instance.container_id)
        if success:
            db_instance.status = "stopped"
            db.commit()
            return {"message": "Container stopped"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop container")

    elif db_instance.instance_type == "vm" and db_instance.pid:
        success = qemu_manager.stop_vm(db_instance.pid)
        if success:
            db_instance.status = "stopped"
            db.commit()
            return {"message": "VM stopped"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop VM")

    else:
        raise HTTPException(status_code=400, detail="Invalid instance type or missing process ID")


@app.delete("/api/instances/{instance_id}")
async def delete_instance(instance_id: int, db: Session = Depends(get_db)):
    """Удаляет инстанс."""
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not db_instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    if db_instance.instance_type == "container" and db_instance.container_id:
        success = docker_manager.delete_container(db_instance.container_id)
        if not success:
            print(f"Container {db_instance.container_id} not found in Docker")

    elif db_instance.instance_type == "vm":
        success = qemu_manager.delete_vm(db_instance.pid, db_instance.image_path)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete VM")

    db.delete(db_instance)
    db.commit()
    return {"message": "Instance deleted"}


@app.get("/api/instances/{instance_id}/stats")
async def get_instance_stats(instance_id: int, db: Session = Depends(get_db)):
    """Получает текущую статистику инстанса."""
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not db_instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    stats = None

    if db_instance.instance_type == "container" and db_instance.container_id:
        stats = docker_manager.get_container_stats(db_instance.container_id)

    elif db_instance.instance_type == "vm":
        if not db_instance.pid:
            raise HTTPException(status_code=400, detail="VM PID not found")
        try:
            process = psutil.Process(db_instance.pid)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)

            stats = {
                "cpu_percent": round(cpu_percent, 2),
                "memory_mb": round(memory_mb, 2),
                "network_rx_bytes": 0,
                "network_tx_bytes": 0
            }
        except psutil.NoSuchProcess:
            raise HTTPException(status_code=404, detail="VM process not found")

    if stats is None:
        raise HTTPException(status_code=500, detail="Could not retrieve stats")

    return stats


@app.get("/api/vms", response_model=List[schemas.InstanceResponse])
async def read_vms(db: Session = Depends(get_db)):
    """Возвращает список всех виртуальных машин."""
    vms = db.query(models.Instance).filter(models.Instance.instance_type == "vm").all()
    return vms


@app.post("/api/vms/create", response_model=schemas.InstanceResponse)
async def create_vm_instance(instance: schemas.InstanceCreate, db: Session = Depends(get_db)):
    """Создает только виртуальную машину."""
    if instance.type != "vm":
        raise HTTPException(status_code=400, detail="This endpoint is only for VMs")

    try:
        vm_data = qemu_manager.create_vm(
            disk_gb=instance.disk,
            ram_mb=instance.ram,
            cpu=instance.cpu
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create VM: {str(e)}")

    db_instance = models.Instance(
        instance_type="vm",
        os=instance.os,
        cpu=instance.cpu,
        ram=instance.ram,
        disk=instance.disk,
        owner=instance.owner,
        status="running",
        ssh_host="localhost",
        ssh_port=vm_data["ssh_port"],
        pid=vm_data["pid"],
        image_path=vm_data["image_path"],
        max_runtime=instance.max_runtime,
        network_limit=instance.network_limit
    )
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)

    return db_instance


@app.post("/api/vms/{instance_id}/stop")
async def stop_vm_instance(instance_id: int, db: Session = Depends(get_db)):
    """Останавливает только виртуальную машину."""
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not db_instance:
        raise HTTPException(status_code=404, detail="VM not found")

    if db_instance.instance_type != "vm":
        raise HTTPException(status_code=400, detail="Instance is not a VM")

    if not db_instance.pid:
        raise HTTPException(status_code=400, detail="VM PID not found")

    success = qemu_manager.stop_vm(db_instance.pid)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop VM")

    db_instance.status = "stopped"
    db.commit()
    return {"message": "VM stopped"}


@app.delete("/api/vms/{instance_id}")
async def delete_vm_instance(instance_id: int, db: Session = Depends(get_db)):
    """Удаляет только виртуальную машину."""
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not db_instance:
        raise HTTPException(status_code=404, detail="VM not found")

    if db_instance.instance_type != "vm":
        raise HTTPException(status_code=400, detail="Instance is not a VM")

    success = qemu_manager.delete_vm(db_instance.pid, db_instance.image_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete VM")

    db.delete(db_instance)
    db.commit()
    return {"message": "VM deleted"}


@app.get("/api/vms/{instance_id}/stats")
async def get_vm_stats(instance_id: int, db: Session = Depends(get_db)):
    """Получает статистику по VM через psutil."""
    db_instance = db.query(models.Instance).filter(models.Instance.id == instance_id).first()
    if not db_instance:
        raise HTTPException(status_code=404, detail="VM not found")

    if db_instance.instance_type != "vm":
        raise HTTPException(status_code=400, detail="Instance is not a VM")

    if not db_instance.pid:
        raise HTTPException(status_code=400, detail="VM PID not found")

    try:
        process = psutil.Process(db_instance.pid)
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = process.cpu_percent(interval=0.1)

        return {
            "pid": db_instance.pid,
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(memory_mb, 2)
        }
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail="VM process not found")


@app.get("/api/monitor/instances", response_model=List[schemas.InstanceResponse])
async def monitor_instances_view(db: Session = Depends(get_db)):
    """Возвращает текущее состояние всех инстансов для мониторинга."""
    instances = db.query(models.Instance).all()
    return instances