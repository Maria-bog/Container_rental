from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
import docker_manager


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



@app.post("/api/instances/create", response_model=schemas.InstanceResponse)
async def create_instance(instance: schemas.InstanceCreate, db: Session = Depends(get_db)):
    """
    Создает новый инстанс (VM или Container).
    """
    ssh_port = None
    container_id = None
    
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
        
        raise HTTPException(status_code=501, detail="VM creation not implemented yet")
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
    elif db_instance.instance_type == "vm":
        
        raise HTTPException(status_code=501, detail="VM stop not implemented")
    else:
        raise HTTPException(status_code=400, detail="Invalid instance type")

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
        
        pass
    
   
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
       
        pass
    
    if stats is None:
        raise HTTPException(status_code=500, detail="Could not retrieve stats")
    
    return stats
