# Vision: ergo-docker-miner

> Simple, reliable Docker-based Ergo (ERG) cryptocurrency mining with lolMiner.

## Target Users

- **Primary**: Home miners with NVIDIA GPUs wanting easy Ergo setup
- **Secondary**: Mining hobbyists preferring containerized deployments

## Strategic Priorities (2025)

1. Keep lolMiner version updated with latest optimizations
2. Add multi-GPU configuration examples
3. Improve monitoring and hashrate logging
4. Document performance tuning for common GPU models

## In Scope

- Docker-based Ergo mining setup
- lolMiner integration
- NVIDIA GPU support (CUDA)
- Environment-based configuration
- Container restart policies

## Out of Scope

- AMD GPU support (NVIDIA focus)
- Mining pool operation (client-side only)
- Profitability calculators
- Other cryptocurrencies (Ergo-focused)

## Success Metrics

| Metric                     | Current | Target              |
| -------------------------- | ------- | ------------------- |
| Setup time                 | ~10 min | <5 min              |
| Documentation completeness | Basic   | GPU-specific guides |
| Container stability        | Good    | 99.9% uptime        |

## Competitive Positioning

- **Primary competitors**: Native lolMiner installs, HiveOS
- **Differentiation**: Docker simplicity, zero-config defaults, portable across machines
