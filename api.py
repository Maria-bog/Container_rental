import requests

BASE_URL = "http://localhost:8000/api"


def create_instance(data):
    r = requests.post(
        f"{BASE_URL}/instances/create",
        json=data
    )
    r.raise_for_status()
    return r.json()


def get_instances():
    r = requests.get(f"{BASE_URL}/instances")
    r.raise_for_status()
    return r.json()


def delete_instance(instance_id):
    r = requests.delete(f"{BASE_URL}/instances/{instance_id}")
    r.raise_for_status()
    return r.json()


def stop_instance(instance_id):
    r = requests.post(f"{BASE_URL}/instances/{instance_id}/stop")
    r.raise_for_status()
    return r.json()