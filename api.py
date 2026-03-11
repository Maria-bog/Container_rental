import requests

BASE_URL = "http://localhost:8000/api"

def create_instance(data):

	r = requests.post(
		f"{BASE_URL}/instances/create",
		json=data
	)

def get_instances():

	r = requests.get(
		f"{BASE_URL}/instances"
	)

	return r.json()

def delete_instance(instance_id):

	requests.delete(
		f"{BASE_URL}/instances/{instance_id}"
	)

def stop_instance(instance_id):

	requests.post(
		f"{BASE_URL}/instances/{instance_id}/stop"
	)
