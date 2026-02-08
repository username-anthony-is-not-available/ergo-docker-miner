# Overclocking Bible: RTX 40-Series for Ergo (Autolykos2)

This guide provides community-tested overclocking settings for NVIDIA RTX 40-series GPUs when mining Ergo (ERG). These settings are designed to maximize efficiency and keep your hardware running cool.

## Safety First

**Disclaimer:** Overclocking can be risky and may damage your hardware if not done correctly. The author of this project is not responsible for any damage caused by the use of these settings. Please use them at your own risk.

- **Start Small:** Always start with conservative settings and gradually increase them.
- **Monitor Temperatures:** Keep a close eye on your GPU temperature and hotspot temperature. For Ergo, GPUs generally run much cooler than on other algorithms like KawPow or Ethash.
- **Stability is Key:** A stable rig that mines for 24 hours is better than a slightly faster rig that crashes every hour.

## General Tips for Ergo Mining

Ergo (Autolykos2) is a memory-intensive algorithm but also benefits from a stable core clock. The Ada Lovelace architecture (RTX 40-series) is exceptionally efficient for this algorithm.

- **Memory Clock:** Increasing the memory clock (VRAM) is the most effective way to increase your hashrate.
- **Power Limit:** RTX 40-series cards often have very high default power limits. For Ergo, you can significantly reduce these limits with minimal impact on hashrate, greatly improving your efficiency (MH/Watt).
- **Core Clock:** While Ergo isn't as core-dependent as some other coins, a slight negative offset or a locked core clock can help reduce power draw and heat.
- **Tuning Presets:** This project includes built-in tuning presets (High, Efficient, Quiet) that prioritize different goals from maximum performance to lowest power draw.

## Recommended Settings (RTX 40-Series)

These settings are derived from the `gpu_profiles.json` included in this project. You can apply them automatically by setting the `GPU_PROFILE` environment variable to your GPU model name.

| GPU Model | Mode | Core Offset | Mem Offset | Power Limit |
|-----------|------|-------------|------------|-------------|
| **RTX 4090** | Performance (High) | -200 | +1500 | 350W |
| | Efficiency (Eco) | -300 | +1500 | 280W |
| | Quiet | -400 | +1500 | 220W |
| **RTX 4080 Super**| Performance (High) | -200 | +1500 | 270W |
| | Efficiency (Eco) | -300 | +1500 | 220W |
| | Quiet | -400 | +1500 | 180W |
| **RTX 4080** | Performance (High) | -200 | +1500 | 250W |
| | Efficiency (Eco) | -300 | +1500 | 200W |
| | Quiet | -400 | +1500 | 160W |
| **RTX 4070 Ti Super**| Performance (High) | -200 | +1300 | 220W |
| | Efficiency (Eco) | -300 | +1300 | 180W |
| | Quiet | -400 | +1300 | 140W |
| **RTX 4070 Ti** | Performance (High) | -200 | +1300 | 200W |
| | Efficiency (Eco) | -300 | +1300 | 160W |
| | Quiet | -400 | +1300 | 130W |
| **RTX 4070 Super**| Performance (High) | -200 | +1300 | 170W |
| | Efficiency (Eco) | -300 | +1300 | 140W |
| | Quiet | -400 | +1300 | 110W |
| **RTX 4070** | Performance (High) | -200 | +1300 | 150W |
| | Efficiency (Eco) | -300 | +1300 | 120W |
| | Quiet | -400 | +1300 | 100W |
| **RTX 4060 Ti** | Performance (High) | -200 | +1200 | 130W |
| | Efficiency (Eco) | -300 | +1200 | 110W |
| | Quiet | -400 | +1200 | 90W |
| **RTX 4060** | Performance (High) | -200 | +1200 | 100W |
| | Efficiency (Eco) | -300 | +1200 | 80W |
| | Quiet | -400 | +1200 | 70W |

## How to Apply These Settings

1.  **Using the Dashboard:** Navigate to the 'Config' tab and select your GPU profile from the dropdown menu.
2.  **Using the Setup Script:** Run `./setup.sh` and follow the prompts to select your GPU model.
3.  **Manual Configuration:** Edit your `.env` file and set:
    ```bash
    APPLY_OC=true
    GPU_PROFILE="RTX 4090"
    # Select tuning preset: High, Efficient, or Quiet
    GPU_TUNING="Efficient"
    ```

## Troubleshooting

- **Rig Crashes:** If your rig crashes or the miner restarts frequently, try reducing the `GPU_MEM_OFFSET` or increasing the `GPU_POWER_LIMIT`.
- **High Temperatures:** If your GPU is running too hot (above 70°C for Ergo), ensure you have adequate airflow and consider using the "Eco" profile.
- **Settings Not Applying:** Ensure the container is running with the necessary privileges and that the NVIDIA Container Toolkit is correctly installed.
