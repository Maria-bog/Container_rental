import os
import socket
import subprocess
import signal
import uuid

# os — работа с системой, файлами, процессами
# socket — работа с портами и сетью
# subprocess — запуск системных команд
# signal — сигналы процессам
# uuid — генерация уникальных id

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VM_DIR = os.path.join(BASE_DIR, "data", "vms")
IMAGE_DIR = os.path.join(BASE_DIR, "data", "base_images")
IMAGE_PATH = os.path.join(IMAGE_DIR, "fedora-base.qcow2")
SSH_PORT_RANGE = range(2300, 2400)


def find_free_port():
    for port in SSH_PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise Exception("Нет свободных портов в заданном диапазоне")


def create_vm(disk_gb, ram_mb, cpu):
    if not os.path.exists(IMAGE_PATH):
        raise Exception("Нет образа")

    if not os.path.exists(VM_DIR):
        os.makedirs(VM_DIR, exist_ok=True)

    ssh_port = find_free_port()

    vm_id = "vm_" + uuid.uuid4().hex[:8]
    file_name = vm_id + ".qcow2"
    new_path = VM_DIR + "/" + file_name

    create_image = [
        "qemu-img",
        "create",
        "-f", "qcow2",
        "-b", IMAGE_PATH,
        "-F", "qcow2",
        new_path,
        f"{disk_gb}G"
    ]

    result = subprocess.run(create_image, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Ошибка создания образа: {result.stderr}")

    qemu_cmd = [
        "qemu-system-x86_64",
        "-m", str(ram_mb),
        "-smp", str(cpu),
        "-drive", f"file={new_path},format=qcow2",
        "-netdev", f"user,id=net0,hostfwd=tcp::{ssh_port}-:22",
        "-device", "e1000,netdev=net0",
        "-nographic"
    ]

    process = subprocess.Popen(
        qemu_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return {
        "vm_id": vm_id,
        "image_path": new_path,
        "ssh_port": ssh_port,
        "pid": process.pid
    }


def stop_vm(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        print(f"Процесс {pid} не найден")
        return False
    except Exception as e:
        print(f"Ошибка остановки VM: {e}")
        return False


def delete_vm(pid: int | None, image_path: str | None):
    if pid:
        stop_vm(pid)

    try:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return True
    except Exception as e:
        print(f"Ошибка удаления VM: {e}")
        return False