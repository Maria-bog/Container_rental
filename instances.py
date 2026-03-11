import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from api import get_instances, stop_instance, delete_instance

st.title("Instances")

st_autorefresh(interval=5000)

instances = get_instances()

df = pd.DataFrame(instances)

st.dataframe(df)

if not instances:
    st.write("No instances running")

for instance in instances:

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.write(instance["id"])
    col2.write(instance["type"])
    col3.write(instance["status"])
    col4.write(instance["cpu"])
    col5.write(instance["ram"])

    ssh_command = f"ssh user@{instance['ssh_host']} -p {instance['ssh_port']}"

    st.code(ssh_command)


    if col6.button(f"Stop {instance['id']}"):
    stop_instance(instance["id"])

    if col6.button(f"Delete {instance['id']}"):
    delete_instance(instance["id"])
