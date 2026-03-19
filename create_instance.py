import streamlit as st
from api import create_instance

st.title("Create Instance")

instance_type = st.selectbox(
    "Instance type",
    ["vm", "container"]
)

os_name = st.selectbox(
    "OS",
    ["fedora", "linuxserver/openssh-server"]
)

cpu = st.slider(
    "CPU cores",
    1,
    8,
    2
)

ram = st.slider(
    "RAM MB",
    512,
    8192,
    2048
)

disk = st.slider(
    "Disk GB",
    5,
    50,
    10
)

owner = st.text_input("Client name")

max_runtime = st.number_input(
    "Max runtime (minutes)",
    min_value=1,
    max_value=1440,
    value=60
)

network_limit = st.number_input(
    "Network limit (MB)",
    min_value=10,
    max_value=10000,
    value=500
)

if st.button("Create instance"):
    data = {
        "type": instance_type,
        "os": os_name,
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "owner": owner,
        "max_runtime": max_runtime,
        "network_limit": network_limit
    }

    try:
        response = create_instance(data)
        st.success("Instance created successfully")
        st.json(response)
    except Exception as e:
        st.error(f"Failed to create instance: {e}")