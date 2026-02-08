import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import os
import json
import subprocess
import logging
from typing import Dict, Any, Optional

import database
from miner_api import get_full_miner_data, get_gpu_names, get_system_info, restart_service, get_node_status, refresh_gpu_names_cache, get_24h_average_hashrate
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
        avg_hashrate_24h = get_24h_average_hashrate()
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
            col_h1, col_h2 = st.columns([4, 1])
            col_h1.write(f"Miner: {data.get('miner', '--')} | Last Updated: {datetime.now().strftime('%H:%M:%S')}")
            if col_h2.button("🔄 Refresh Data"):
                refresh_gpu_names_cache()
                st.rerun()

            # Top Stats
            num_cols = 8 if data.get('total_dual_hashrate', 0) > 0 else 7
            cols = st.columns(num_cols)

            cols[0].metric("Current Hashrate", f"{data.get('total_hashrate', 0):.2f} MH/s")
            cols[1].metric("24h Avg Hashrate", f"{avg_hashrate_24h:.2f} MH/s")

            curr_col = 2
            if data.get('total_dual_hashrate', 0) > 0:
                cols[curr_col].metric("Dual Hashrate", f"{data.get('total_dual_hashrate', 0):.2f} MH/s")
                curr_col += 1

            cols[curr_col].metric("Total Power", f"{data.get('total_power_draw', 0):.1f} W")
            cols[curr_col+1].metric("Avg Temp", f"{data.get('avg_temperature', 0):.1f} °C")
            cols[curr_col+2].metric("Efficiency", f"{data.get('efficiency', 0):.3f} MH/W")
            cols[curr_col+3].metric("Uptime", format_uptime(data.get('uptime', 0)))

            if node_status.get('enabled'):
                node_text = "Synced" if node_status.get('is_synced') else "Syncing..."
                if node_status.get('error'): node_text = "Error"
                cols[curr_col+4].metric("Ergo Node", node_text, delta=f"{node_status.get('full_height', 0)} / {node_status.get('headers_height', 0)}", delta_color="normal")
            else:
                cols[curr_col+4].metric("Ergo Node", "Disabled")

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
                for service, s_info in services.items():
                    s_col1, s_col2 = st.columns([3, 1])
                    status = s_info.get('status', 'Unknown')
                    uptime = s_info.get('uptime', 0)
                    uptime_str = f" (Up {format_uptime(uptime)})" if status == 'Running' and uptime > 0 else ""
                    s_col1.write(f"**{service}:** {status}{uptime_str}")
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

            st.subheader("Efficiency History")
            df['efficiency'] = df['hashrate'] / df['total_power_draw'].replace(0, float('nan'))
            fig_eff = px.line(df, x='timestamp', y='efficiency',
                                labels={'efficiency': 'Efficiency (MH/W)', 'timestamp': 'Time'},
                                title="Rig-wide Efficiency over Time")
            st.plotly_chart(fig_eff, use_container_width=True)

            # Per-GPU History Section
            st.divider()
            st.subheader("Per-GPU History")
            gpu_indices = database.get_gpu_indices(days=days)
            if gpu_indices:
                selected_gpu = st.selectbox("Select GPU", gpu_indices, format_func=lambda x: f"GPU {x}")
                gpu_history = database.get_gpu_history(gpu_index=selected_gpu, days=days)
                if gpu_history:
                    gdf = pd.DataFrame(gpu_history)
                    gdf['timestamp'] = pd.to_datetime(gdf['timestamp'])

                    col_g1, col_g2 = st.columns(2)

                    fig_gh = px.line(gdf, x='timestamp', y='hashrate',
                                    labels={'hashrate': 'Hashrate (MH/s)', 'timestamp': 'Time'},
                                    title=f"GPU {selected_gpu} Hashrate")
                    col_g1.plotly_chart(fig_gh, use_container_width=True)

                    fig_gp = px.line(gdf, x='timestamp', y='power_draw',
                                    labels={'power_draw': 'Power (W)', 'timestamp': 'Time'},
                                    title=f"GPU {selected_gpu} Power Draw")
                    col_g2.plotly_chart(fig_gp, use_container_width=True)

                    fig_gt = px.line(gdf, x='timestamp', y=['temperature', 'fan_speed'],
                                    labels={'value': 'Value', 'timestamp': 'Time'},
                                    title=f"GPU {selected_gpu} Temp & Fan")
                    st.plotly_chart(fig_gt, use_container_width=True)
            else:
                st.info("No per-GPU historical data available.")

            # Weekly Report Section
            st.divider()
            st.subheader("Weekly Summary Report")
            data_dir = os.getenv('DATA_DIR', '.')
            report_file = os.path.join(data_dir, 'weekly_report.txt')
            if os.path.exists(report_file):
                with open(report_file, 'r') as f:
                    st.text_area("Report Content", value=f.read(), height=200)
            else:
                st.info("Weekly report not yet generated. The report generator runs in the background.")

            # Provide CSV download (generated on-the-fly from database)
            st.subheader("Data Export")

            @st.cache_data(ttl=60)
            def get_csv_data(days_to_export):
                temp_csv = os.path.join(data_dir, f'history_export_{days_to_export}d.csv')
                if database.export_history_to_csv(temp_csv, days=days_to_export):
                    with open(temp_csv, 'rb') as f:
                        return f.read()
                return None

            csv_data = get_csv_data(days)
            if csv_data:
                st.download_button(
                    label="Download Mining History CSV",
                    data=csv_data,
                    file_name=f"mining_history_{days}d.csv",
                    mime="text/csv",
                    help=f"Download full history for the last {days} days as a CSV file."
                )

            # Clear History Button
            st.divider()
            with st.expander("🗑️ Danger Zone"):
                st.warning("Clearing history will permanently delete all records from the database.")
                if st.button("Clear All Mining History"):
                    database.clear_history()
                    st.success("History cleared!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("No history data available")
            if st.button("Refresh History"):
                st.rerun()

    elif page == "Configuration":
        st.title("Configuration")

        config = read_env_file()

        with st.form("config_form"):
            # 1. Wallet & Pool
            st.subheader("🌐 Wallet & Pool")
            col1, col2 = st.columns(2)
            wallet = col1.text_input("Wallet Address", value=os.getenv('WALLET_ADDRESS', config.get('WALLET_ADDRESS', '')), help="Your Ergo wallet address.")
            worker = col2.text_input("Worker Name", value=config.get('WORKER_NAME', 'ergo-miner'), help="Name for this mining rig.")

            pool = col1.text_input("Primary Pool Address", value=config.get('POOL_ADDRESS', ''), help="Primary mining pool stratum address.")
            backup_pool = col2.text_input("Backup Pool Address", value=config.get('BACKUP_POOL_ADDRESS', ''), help="Failover pool address.")

            # 2. Miner Settings
            st.subheader("⛏️ Miner Settings")
            col3, col4 = st.columns(2)
            miner_options = ["lolminer", "t-rex"]
            current_miner = config.get('MINER', 'lolminer').lower()
            miner_idx = miner_options.index(current_miner) if current_miner in miner_options else 0
            miner = col3.selectbox("Miner Backend", miner_options, index=miner_idx)

            gpu_devices = col4.text_input("GPU Devices", value=config.get('GPU_DEVICES', 'AUTO'), help="Comma-separated IDs (e.g. 0,1,2) or AUTO.")

            multi_process = col3.checkbox("Multi-Process Mode", value=config.get('MULTI_PROCESS', 'false').lower() == 'true', help="Run one miner process per GPU for better stability.")
            extra_args = col4.text_input("Extra Arguments", value=config.get('EXTRA_ARGS', ''), help="Additional command line flags for the miner.")

            # 3. Overclocking & Tuning
            st.subheader("⚙️ Overclocking & Tuning")
            col5, col6 = st.columns(2)
            apply_oc = col5.checkbox("Apply Overclocking", value=config.get('APPLY_OC', 'false').lower() == 'true')

            # Load profiles for dynamic selection
            profiles = {}
            if os.path.exists('gpu_profiles.json'):
                try:
                    with open('gpu_profiles.json', 'r') as f:
                        profiles = json.load(f)
                except Exception:
                    pass

            base_profiles = sorted(list(set([p.split(' (')[0] for p in profiles.keys()])))
            current_profile = config.get('GPU_PROFILE', 'AUTO')

            profile_idx = 0
            if current_profile != 'AUTO' and current_profile.split(' (')[0] in base_profiles:
                profile_idx = base_profiles.index(current_profile.split(' (')[0]) + 1
            elif current_profile == 'AUTO':
                profile_idx = 0

            selected_profile = col5.selectbox("GPU Model Profile", ["AUTO"] + base_profiles, index=profile_idx, help="Select your GPU model for optimized settings.")

            # Dynamic Tuning Presets based on selected profile
            tuning_options = ["High"]
            if selected_profile != "AUTO":
                if f"{selected_profile} (Eco)" in profiles: tuning_options.append("Efficient")
                if f"{selected_profile} (Quiet)" in profiles: tuning_options.append("Quiet")
            else:
                tuning_options = ["High", "Efficient", "Quiet"]

            current_tuning = config.get('GPU_TUNING', 'Efficient')
            tuning_idx = tuning_options.index(current_tuning) if current_tuning in tuning_options else (1 if "Efficient" in tuning_options else 0)
            tuning = col6.selectbox("Tuning Preset", tuning_options, index=tuning_idx, help="High=Max Hashrate, Efficient=Best MH/W, Quiet=Lower Fans/Power.")

            # 4. Dual Mining
            with st.expander("🔗 Dual Mining (lolMiner Only)"):
                dual_algo_options = ["", "KASPADUAL", "ALEPHDUAL"]
                current_dual_algo = config.get('DUAL_ALGO', '')
                dual_algo_idx = dual_algo_options.index(current_dual_algo) if current_dual_algo in dual_algo_options else 0
                dual_algo = st.selectbox("Dual Algorithm", dual_algo_options, index=dual_algo_idx)

                col7, col8 = st.columns(2)
                dual_pool = col7.text_input("Dual Pool Address", value=config.get('DUAL_POOL', ''))
                dual_wallet = col8.text_input("Dual Wallet Address", value=config.get('DUAL_WALLET', ''))
                dual_worker = col7.text_input("Dual Worker Name", value=config.get('DUAL_WORKER', ''))

            # 5. Advanced Features
            st.subheader("🚀 Advanced Features")
            col9, col10 = st.columns(2)
            profit_switch = col9.checkbox("Auto Profit Switching", value=config.get('ENABLE_PROFIT_SWITCHER', 'false').lower() == 'true' or config.get('AUTO_PROFIT_SWITCHING', 'false').lower() == 'true')
            cuda_restart = col10.checkbox("Auto Restart on CUDA Error", value=config.get('AUTO_RESTART_ON_CUDA_ERROR', 'false').lower() == 'true')

            node_check = col9.checkbox("Ergo Node Sync Check", value=config.get('CHECK_NODE_SYNC', 'false').lower() == 'true')
            node_url = col10.text_input("Node API URL", value=config.get('NODE_URL', 'http://localhost:9053'))

            if profit_switch:
                with st.expander("📈 Profit Switching Settings"):
                    col11, col12 = st.columns(2)
                    ps_threshold = col11.number_input("Switching Threshold", value=float(config.get('PROFIT_SWITCHING_THRESHOLD', '0.005')), format="%.4f", step=0.001, help="Min profit gain to trigger switch (0.005 = 0.5%)")
                    ps_interval = col12.number_input("Check Interval (seconds)", value=int(config.get('PROFIT_SWITCHING_INTERVAL', '3600')), step=60)
                    ps_cooldown = col11.number_input("Minimum Switch Cooldown (seconds)", value=int(config.get('MIN_SWITCH_COOLDOWN', '900')), step=60)

            # 6. Telegram Notifications
            with st.expander("📱 Telegram Notifications"):
                tg_enable = st.checkbox("Enable Telegram Alerts", value=config.get('TELEGRAM_ENABLE', 'false').lower() == 'true')
                tg_token = st.text_input("Bot Token", value=config.get('TELEGRAM_BOT_TOKEN', ''), type="password")
                tg_chat_id = st.text_input("Chat ID", value=config.get('TELEGRAM_CHAT_ID', ''))
                tg_threshold = st.number_input("Notification Grace Period (seconds)", value=int(config.get('TELEGRAM_NOTIFY_THRESHOLD', '300')), step=60)

            submit = st.form_submit_button("Save Configuration")

            if submit:
                new_config = config.copy()
                new_config['WALLET_ADDRESS'] = wallet
                new_config['POOL_ADDRESS'] = pool
                new_config['BACKUP_POOL_ADDRESS'] = backup_pool
                new_config['WORKER_NAME'] = worker
                new_config['MINER'] = miner
                new_config['GPU_DEVICES'] = gpu_devices
                new_config['MULTI_PROCESS'] = 'true' if multi_process else 'false'
                new_config['EXTRA_ARGS'] = extra_args
                new_config['APPLY_OC'] = 'true' if apply_oc else 'false'
                new_config['GPU_PROFILE'] = selected_profile
                new_config['GPU_TUNING'] = tuning

                # Dual Mining
                new_config['DUAL_ALGO'] = dual_algo
                new_config['DUAL_POOL'] = dual_pool
                new_config['DUAL_WALLET'] = dual_wallet
                new_config['DUAL_WORKER'] = dual_worker

                # Features
                new_config['ENABLE_PROFIT_SWITCHER'] = 'true' if profit_switch else 'false'
                new_config['AUTO_PROFIT_SWITCHING'] = 'true' if profit_switch else 'false'
                new_config['AUTO_RESTART_ON_CUDA_ERROR'] = 'true' if cuda_restart else 'false'
                new_config['CHECK_NODE_SYNC'] = 'true' if node_check else 'false'
                new_config['NODE_URL'] = node_url

                # Profit Switching Advanced
                if profit_switch:
                    new_config['PROFIT_SWITCHING_THRESHOLD'] = str(ps_threshold)
                    new_config['PROFIT_SWITCHING_INTERVAL'] = str(ps_interval)
                    new_config['MIN_SWITCH_COOLDOWN'] = str(ps_cooldown)

                # Telegram
                new_config['TELEGRAM_ENABLE'] = 'true' if tg_enable else 'false'
                new_config['TELEGRAM_BOT_TOKEN'] = tg_token
                new_config['TELEGRAM_CHAT_ID'] = tg_chat_id
                new_config['TELEGRAM_NOTIFY_THRESHOLD'] = str(tg_threshold)

                write_env_file(new_config)
                st.success("Configuration saved successfully! Restart the miner to apply changes.")

        if st.button("Restart Miner"):
            try:
                subprocess.run(['./restart.sh'], check=True)
                st.info("Restart command sent...")
            except Exception as e:
                st.error(f"Failed to restart miner: {e}")

    elif page == "Logs":
        st.title("System & Miner Logs")
        data_dir = os.getenv('DATA_DIR', '.')

        # Discover available log files
        # Include both miner logs and background service logs
        service_logs = [f for f in os.listdir(data_dir) if f.endswith('.log') and not f.startswith('miner')]
        miner_logs = [f for f in os.listdir(data_dir) if f.startswith('miner') and f.endswith('.log')]

        service_logs.sort()
        miner_logs.sort()

        all_logs = service_logs + miner_logs

        if not all_logs:
            st.info("No log files found. Waiting for services to start...")
        else:
            selected_log = st.selectbox("Select Log File", all_logs)
            log_path = os.path.join(data_dir, selected_log)

            if os.path.exists(log_path):
                with open(log_path, 'r', errors='replace') as f:
                    # For large logs, read only the last part
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    # Read last 50KB or so
                    f.seek(max(0, size - 51200))
                    content = f.read()
                    lines = content.splitlines()

                    st.text_area(f"Latest entries from {selected_log}", value="\n".join(lines[-100:]), height=400)

                with open(log_path, 'rb') as f:
                    st.download_button(f"Download {selected_log}", data=f, file_name=selected_log, mime="text/plain")

    elif page == "Pool Stats":
        st.title("Pool Profitability")
        st.write("Real-time profitability analysis across supported Ergo pools.")

        stats = []
        for pool in profit_switcher.POOLS:
            details = profit_switcher.get_pool_profitability(pool, return_details=True)
            stats.append({
                "Pool": pool["name"],
                "Score": round(details['score'], 4),
                "Effort (Luck)": f"{details['effort']*100:.1f}%",
                "Fee": f"{details['fee']*100:.1f}%",
                "Address": pool["stratum"]
            })

        df_stats = pd.DataFrame(stats)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)

        st.info("💡 **Score** is calculated as `(1 - Fee) / Effort`. Higher score means better profitability. Effort is estimated from pool's luck/effort statistics where available.")

if __name__ == "__main__":
    main()
