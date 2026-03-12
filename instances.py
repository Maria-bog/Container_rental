import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from api import get_instances, stop_instance, delete_instance

st.title("Instances")

st_autorefresh(interval=5000, key="instances_refresh")

try:
    instances = get_instances()
except Exception as e:
    st.error(f"Failed to load instances: {e}")
    instances = []

if not instances:
    st.write("No instances running")
else:
    df = pd.DataFrame(instances)
    st.dataframe(df)

    for instance in instances:
        st.markdown("---")
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        col1.write(instance["id"])
        col2.write(instance["instance_type"])
        col3.write(instance["status"])
        col4.write(instance["cpu"])
        col5.write(instance["ram"])

        ssh_command = f"ssh user@{instance['ssh_host']} -p {instance['ssh_port']}"
        st.code(ssh_command)

        if col6.button(f"Stop {instance['id']}", key=f"stop_{instance['id']}"):
            try:
                stop_instance(instance["id"])
                st.success(f"Instance {instance['id']} stopped")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to stop instance {instance['id']}: {e}")

        if col6.button(f"Delete {instance['id']}", key=f"delete_{instance['id']}"):
            try:
                delete_instance(instance["id"])
                st.success(f"Instance {instance['id']} deleted")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete instance {instance['id']}: {e}")