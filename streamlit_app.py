import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import os
import subprocess
import logging
from typing import Dict, Any, Optional

import database
from miner_api import get_full_miner_data, get_gpu_names, get_system_info, restart_service, get_node_status
from env_config import read_env_file, write_env_file
import profit_switcher

def format_uptime(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"

def format_host_uptime(seconds: float) -> str:
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    return f"{d}d {h}h {m}m"

def main():
    # Initialize database
    database.init_db()

    # Page config
    st.set_page_config(page_title="Miner Dashboard", layout="wide")

    # Styling
    st.markdown("""
        <style>
        .status-mining { color: #4caf50; font-weight: bold; }
        .status-error { color: #f44336; font-weight: bold; }
        .status-warning { color: #ff9800; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

    # Navigation
    page = st.sidebar.radio("Navigation", ["Dashboard", "History", "Configuration", "Logs", "Pool Stats"])

    if page == "Dashboard":
        st.title("Miner Dashboard")

        # Placeholder for real-time data
        placeholder = st.empty()

        data = get_full_miner_data()
        system_info = get_system_info()
        node_status = get_node_status()

        if not data:
            data = {'status': 'Error: Miner API unreachable', 'total_hashrate': 0, 'total_power_draw': 0, 'efficiency': 0, 'avg_temperature': 0, 'uptime': 0}

        # Update status if node not synced
        if node_status.get('enabled') and not node_status.get('is_synced'):
            data['status'] = 'Waiting for Node Sync'

        with placeholder.container():
            # Header Status
            status_val = data.get('status', 'Unknown')
            status_color = "status-mining" if status_val == 'Mining' else "status-error" if "Error" in status_val else "status-warning"
            st.markdown(f"### Status: <span class='{status_color}'>{status_val}</span>", unsafe_allow_html=True)
            st.write(f"Miner: {data.get('miner', '--')} | Last Updated: {datetime.now().strftime('%H:%M:%S')}")

            # Top Stats
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.metric("Total Hashrate", f"{data.get('total_hashrate', 0):.2f} MH/s")
            if data.get('total_dual_hashrate', 0) > 0:
                col2.metric("Dual Hashrate", f"{data.get('total_dual_hashrate', 0):.2f} MH/s")
            else:
                col2.metric("Total Power", f"{data.get('total_power_draw', 0):.1f} W")
            col3.metric("Avg Temp", f"{data.get('avg_temperature', 0):.1f} °C")
            col4.metric("Efficiency", f"{data.get('efficiency', 0):.3f} MH/W")
            col5.metric("Uptime", format_uptime(data.get('uptime', 0)))

            if node_status.get('enabled'):
                node_text = "Synced" if node_status.get('is_synced') else "Syncing..."
                if node_status.get('error'): node_text = "Error"
                col6.metric("Ergo Node", node_text, delta=f"{node_status.get('full_height', 0)} / {node_status.get('headers_height', 0)}", delta_color="normal")
            else:
                col6.metric("Ergo Node", "Disabled")

            # GPUs
            st.subheader("GPUs")
            if data.get('gpus'):
                gpu_df = pd.DataFrame(data['gpus'])
                # Reorder and rename columns for display
                display_cols = ['index', 'hashrate', 'temperature', 'power_draw', 'fan_speed', 'efficiency', 'accepted_shares', 'rejected_shares']
                if data.get('total_dual_hashrate', 0) > 0:
                    display_cols.insert(2, 'dual_hashrate')

                st.dataframe(gpu_df[display_cols].set_index('index'), use_container_width=True)
            else:
                st.info("No GPU data available")

            # System Info & Services
            col_sys, col_ser = st.columns(2)

            with col_sys:
                st.subheader("System Information")
                st.write(f"**CPU Usage:** {system_info.get('cpu_usage', 0):.1f}%")
                st.write(f"**RAM Usage:** {system_info.get('memory_usage', 0):.1f}%")
                st.write(f"**Disk Usage:** {system_info.get('disk_usage', 0):.1f}%")
                st.write(f"**Host Uptime:** {format_host_uptime(system_info.get('host_uptime', 0))}")

            with col_ser:
                st.subheader("Service Status")
                services = system_info.get('services', {})
                for service, status in services.items():
                    s_col1, s_col2 = st.columns([3, 1])
                    s_col1.write(f"**{service}:** {status}")
                    if s_col2.button("Restart", key=f"restart_{service}"):
                        if restart_service(service):
                            st.success(f"Restarted {service}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to restart {service}")

        # Auto-refresh
        time.sleep(5)
        st.rerun()

    elif page == "History":
        st.title("Mining History")

        days = st.sidebar.slider("History Range (Days)", 1, 30, 7)
        history = database.get_history(days=days)

        if history:
            df = pd.DataFrame(history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            st.subheader("Hashrate History")
            # Determine which hashrates to show
            hashrate_cols = ['hashrate']
            if df['dual_hashrate'].sum() > 0:
                hashrate_cols.append('dual_hashrate')

            fig_hashrate = px.line(df, x='timestamp', y=hashrate_cols,
                                labels={'value': 'Hashrate (MH/s)', 'timestamp': 'Time'},
                                title="Total Hashrate over Time")
            st.plotly_chart(fig_hashrate, use_container_width=True)

            st.subheader("Power Draw History")
            fig_power = px.line(df, x='timestamp', y='total_power_draw',
                                labels={'total_power_draw': 'Power (W)', 'timestamp': 'Time'},
                                title="Total Power Draw over Time")
            st.plotly_chart(fig_power, use_container_width=True)

            st.subheader("Temperature & Fan Speed")
            fig_temp = px.line(df, x='timestamp', y=['avg_temp', 'avg_fan_speed'],
                                labels={'value': 'Value', 'timestamp': 'Time'},
                                title="Average Temp and Fan Speed")
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("No history data available")

    elif page == "Configuration":
        st.title("Configuration")

        config = read_env_file()

        with st.form("config_form"):
            # Group settings
            st.subheader("Wallet & Pool")
            wallet = st.text_input("Wallet Address", value=os.getenv('WALLET_ADDRESS', config.get('WALLET_ADDRESS', '')))
            pool = st.text_input("Pool Address", value=config.get('POOL_ADDRESS', ''))
            worker = st.text_input("Worker Name", value=config.get('WORKER_NAME', 'ergo-miner'))

            st.subheader("Miner Settings")
            miner_options = ["lolminer", "t-rex"]
            current_miner = config.get('MINER', 'lolminer')
            miner_idx = miner_options.index(current_miner) if current_miner in miner_options else 0
            miner = st.selectbox("Miner", miner_options, index=miner_idx)

            gpu_devices = st.text_input("GPU Devices (e.g., 0,1,2 or AUTO)", value=config.get('GPU_DEVICES', 'AUTO'))
            multi_process = st.checkbox("Multi-Process Mode", value=config.get('MULTI_PROCESS', 'false').lower() == 'true')

            st.subheader("Features")
            col_f1, col_f2 = st.columns(2)
            profit_switch = col_f1.checkbox("Auto Profit Switching", value=config.get('ENABLE_PROFIT_SWITCHER', 'false').lower() == 'true')
            cuda_restart = col_f2.checkbox("Auto Restart on CUDA Error", value=config.get('AUTO_RESTART_ON_CUDA_ERROR', 'false').lower() == 'true')

            node_check = col_f1.checkbox("Ergo Node Sync Check", value=config.get('CHECK_NODE_SYNC', 'false').lower() == 'true')
            node_url = col_f2.text_input("Node URL", value=config.get('NODE_URL', 'http://localhost:9053'))

            st.subheader("Tuning")
            tuning_options = ["High", "Efficient", "Quiet"]
            current_tuning = config.get('GPU_TUNING', 'Efficient')
            tuning_idx = tuning_options.index(current_tuning) if current_tuning in tuning_options else 1
            tuning = st.selectbox("Tuning Preset", tuning_options, index=tuning_idx)

            submit = st.form_submit_button("Save Configuration")

            if submit:
                new_config = config.copy()
                new_config['WALLET_ADDRESS'] = wallet
                new_config['POOL_ADDRESS'] = pool
                new_config['WORKER_NAME'] = worker
                new_config['MINER'] = miner
                new_config['GPU_DEVICES'] = gpu_devices
                new_config['MULTI_PROCESS'] = 'true' if multi_process else 'false'
                new_config['ENABLE_PROFIT_SWITCHER'] = 'true' if profit_switch else 'false'
                new_config['AUTO_RESTART_ON_CUDA_ERROR'] = 'true' if cuda_restart else 'false'
                new_config['CHECK_NODE_SYNC'] = 'true' if node_check else 'false'
                new_config['NODE_URL'] = node_url
                new_config['GPU_TUNING'] = tuning

                write_env_file(new_config)
                st.success("Configuration saved successfully! Restart the miner to apply changes.")

        if st.button("Restart Miner"):
            try:
                subprocess.run(['./restart.sh'], check=True)
                st.info("Restart command sent...")
            except Exception as e:
                st.error(f"Failed to restart miner: {e}")

    elif page == "Logs":
        st.title("Miner Logs")

        if os.path.exists('miner.log'):
            with open('miner.log', 'r') as f:
                lines = f.readlines()
                st.text_area("Last 100 lines", value="".join(lines[-100:]), height=400)

            with open('miner.log', 'rb') as f:
                st.download_button("Download Full Log", data=f, file_name="miner.log", mime="text/plain")
        else:
            st.info("Miner log file not found. Waiting for miner to start...")

    elif page == "Pool Stats":
        st.title("Pool Profitability")

        stats = []
        for pool in profit_switcher.POOLS:
            score = profit_switcher.get_pool_profitability(pool)
            stats.append({
                "Pool": pool["name"],
                "Address": pool["stratum"],
                "Score": round(score, 4)
            })

        st.table(stats)

if __name__ == "__main__":
    main()
