# 24/7 Simulation Daemon

Continuous background process that simulates realistic agent operations and guardrail testing with variable load patterns based on busy/non-busy hours.

## Overview

The simulation daemon runs continuously (24/7) and automatically:
- Executes agent operations and guardrail tests every 15 minutes (configurable)
- Adjusts load based on busy hours (business hours) vs quiet hours (nights/weekends)
- Generates 3000-5000 total requests per day
- Logs all activity comprehensively
- Handles errors gracefully with automatic recovery
- Generates daily summary reports

## Quick Start

### 1. Start the Daemon

```bash
./daemon_manager.sh start
```

### 2. Check Status

```bash
./daemon_manager.sh status
```

### 3. Monitor Logs

```bash
./daemon_manager.sh logs
# or
tail -f daemon_results/simulation_daemon.log
```

### 4. Stop the Daemon

```bash
./daemon_manager.sh stop
```

## Load Profiles

The daemon automatically adjusts load based on time of day:

### Busy Hours (Higher Load)
- **Weekdays**: 8AM - 6PM (configurable)
- **Weekends**: 10AM - 4PM (configurable)
- Operations: 30-60 calls per execution
- Guardrails: 15-30 tests per execution

### Normal Hours (Medium Load)
- Daytime outside busy hours
- Operations: 15-30 calls per execution
- Guardrails: 8-15 tests per execution

### Quiet Hours (Lower Load)
- **11PM - 6AM** every day
- Operations: 5-15 calls per execution
- Guardrails: 3-8 tests per execution

## Daily Request Calculation

With default configuration (15-minute execution interval):
- **96 executions per day** (24 hours × 4 executions/hour)
- **Mix**: 70% operations, 30% guardrails
- **Average requests per execution**: ~40-50
- **Daily total**: ~3800-4800 requests ✓

Breakdown:
- Busy hours (~8 hrs): 32 executions × 45 avg = 1,440 requests
- Normal hours (~8 hrs): 32 executions × 23 avg = 736 requests
- Quiet hours (~8 hrs): 32 executions × 10 avg = 320 requests
- **Total**: ~2,500-2,700 from each simulation type

## Configuration

### Main Configuration File: `simulation_daemon_config.json`

Key settings you can adjust:

```json
{
  "execution_interval_minutes": 15,
  "target_daily_requests": {
    "min": 3000,
    "max": 5000
  },
  "busy_hours": {
    "weekday": {
      "start_hour": 8,
      "end_hour": 18
    }
  },
  "simulation_mix": {
    "operations_weight": 70,
    "guardrails_weight": 30
  }
}
```

### Test Configuration: `simulation_daemon_config.test.json`

For testing with shorter intervals:

```bash
python simulation_daemon.py --config simulation_daemon_config.test.json
```

## Management Commands

### Using daemon_manager.sh

```bash
# Start daemon
./daemon_manager.sh start

# Stop daemon
./daemon_manager.sh stop

# Restart daemon
./daemon_manager.sh restart

# Show status and recent logs
./daemon_manager.sh status

# Tail logs in real-time
./daemon_manager.sh logs

# Show help
./daemon_manager.sh help
```

### Manual Python Execution (for testing)

```bash
# Run with default config
python simulation_daemon.py

# Run with custom config
python simulation_daemon.py --config simulation_daemon_config.test.json

# Run in foreground (see output directly)
python simulation_daemon.py

# Run in background (production)
nohup python simulation_daemon.py > daemon_results/daemon_stdout.log 2>&1 &
```

## Output Files and Directories

```
daemon_results/
├── simulation_daemon.log              # Main log file
├── daemon_stdout.log                  # Standard output
├── daemon_stderr.log                  # Standard error
├── daemon.pid                         # Process ID file
├── continuous_operations_metrics.csv  # All operations metrics (appended)
├── continuous_guardrail_results.csv   # All guardrail results (appended)
└── daily_summaries/
    ├── summary_2026-01-06.json        # Daily summary for Jan 6
    ├── summary_2026-01-07.json        # Daily summary for Jan 7
    └── ...
```

### Log File Example

```
2026-01-06 10:30:00 [INFO] Execution cycle at 2026-01-06 10:30:00
2026-01-06 10:30:00 [INFO] Load profile: BUSY
2026-01-06 10:30:00 [INFO] Simulation type: OPERATIONS
2026-01-06 10:30:00 [INFO] Today's totals so far - Operations: 245, Guardrails: 98
2026-01-06 10:30:00 [INFO] Starting OPERATIONS simulation - calls=45, threads=7, delay=0.5
2026-01-06 10:32:34 [INFO] ✓ Operations simulation completed successfully (45 calls)
2026-01-06 10:32:34 [INFO] Next execution scheduled at 2026-01-06 10:45:00
```

### Daily Summary Example

```json
{
  "date": "2026-01-06",
  "total_operations": 2856,
  "total_guardrails": 1234,
  "total_requests": 4090,
  "target_min": 3000,
  "target_max": 5000,
  "target_met": true
}
```

## Production Deployment with systemd

For production environments, use systemd for automatic startup and monitoring:

### 1. Install the Service

```bash
# Copy service file
sudo cp simulation-daemon.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable simulation-daemon

# Start service
sudo systemctl start simulation-daemon
```

### 2. Manage the Service

```bash
# Check status
sudo systemctl status simulation-daemon

# View logs
sudo journalctl -u simulation-daemon -f

# Stop service
sudo systemctl stop simulation-daemon

# Restart service
sudo systemctl restart simulation-daemon

# Disable autostart
sudo systemctl disable simulation-daemon
```

## Monitoring and Maintenance

### Real-time Monitoring

```bash
# Watch log file
tail -f daemon_results/simulation_daemon.log

# Watch with grep filter
tail -f daemon_results/simulation_daemon.log | grep --line-buffered "✓\|✗\|ERROR"

# Monitor process
watch -n 5 'ps aux | grep simulation_daemon.py'
```

### Daily Summary Review

```bash
# View today's summary
cat daemon_results/daily_summaries/summary_$(date +%Y-%m-%d).json

# View yesterday's summary
cat daemon_results/daily_summaries/summary_$(date -d yesterday +%Y-%m-%d).json

# List all summaries
ls -lh daemon_results/daily_summaries/
```

### Analyzing Results

```bash
# Count total operations executed
wc -l daemon_results/continuous_operations_metrics.csv

# Count total guardrail tests
wc -l daemon_results/continuous_guardrail_results.csv

# Check for failures in operations
grep ",False," daemon_results/continuous_operations_metrics.csv | wc -l

# View recent activity
tail -100 daemon_results/simulation_daemon.log
```

## Error Handling

The daemon implements robust error handling:

### Consecutive Failure Protection
- Tracks consecutive failures
- After 5 consecutive failures, enters 10-minute cooldown
- Automatically resumes after cooldown

### Rate Limiting
- If Azure API returns rate limit errors
- Daemon will slow down and retry
- Configurable in `error_handling` section

### Graceful Shutdown
- Responds to SIGTERM and SIGINT signals
- Completes current operation before shutting down
- Generates final daily summary
- Properly closes all resources

## Troubleshooting

### Daemon Won't Start

```bash
# Check if already running
./daemon_manager.sh status

# Check for errors in stderr
cat daemon_results/daemon_stderr.log

# Verify Python environment
source .venv/bin/activate
python simulation_daemon.py --config simulation_daemon_config.json
```

### High Error Rate

```bash
# Check recent errors
grep ERROR daemon_results/simulation_daemon.log | tail -20

# Verify Azure authentication
az account show

# Check agent availability
head -5 created_agents_results.csv
```

### Daemon Stops Unexpectedly

```bash
# Check system logs
sudo journalctl -xe | grep simulation-daemon

# Check for OOM (out of memory)
dmesg | grep -i "out of memory"

# Reduce thread count in config
# Edit simulation_daemon_config.json, reduce threads
```

### Low Daily Request Count

```bash
# Check if daemon is running continuously
./daemon_manager.sh status

# Review daily summary
cat daemon_results/daily_summaries/summary_$(date +%Y-%m-%d).json

# Increase execution frequency
# Edit config: "execution_interval_minutes": 10
```

## Testing the Daemon

### Short Test Run (10 minutes)

Create `simulation_daemon_config.test.json`:

```json
{
  "execution_interval_minutes": 2,
  "load_profiles": {
    "busy": {
      "operations": {"num_calls": {"min": 5, "max": 10}, ...},
      "guardrails": {"num_tests": {"min": 3, "max": 5}, ...}
    }
  }
}
```

Run test:

```bash
python simulation_daemon.py --config simulation_daemon_config.test.json
# Let it run for 10 minutes, then Ctrl+C
# Check logs and output files
```

## Performance Considerations

### CPU Usage
- Typical: 5-15% during simulations
- Peak: 30-50% during busy hours with high thread counts
- Idle: <1% between executions

### Memory Usage
- Typical: 100-300 MB
- Peak: 500-800 MB with high thread counts
- Consider reducing threads if memory constrained

### Disk Usage
- Logs: ~50-100 MB/day (with rotation recommended)
- CSV files: ~10-20 MB/day
- Daily summaries: <1 MB total

### Network Usage
- Typical: 1-2 Mbps during active simulation
- Peak: 5-10 Mbps during busy hours
- Total daily: ~2-5 GB

## Best Practices

### For Production

1. **Use systemd service** for automatic restart and boot startup
2. **Set up log rotation** to prevent disk fill
3. **Monitor daily summaries** to ensure target metrics are met
4. **Set up alerting** if daemon stops or error rate exceeds threshold
5. **Regular review** of error logs weekly

### For Development/Testing

1. **Use daemon_manager.sh** for easy control
2. **Test configuration** with short intervals first
3. **Monitor logs actively** during initial runs
4. **Adjust parameters** based on actual performance

### Resource Optimization

1. **Reduce threads** if CPU/memory constrained
2. **Increase delay** if hitting rate limits
3. **Adjust execution interval** to meet exact daily targets
4. **Use quiet hours** to reduce off-peak load

## Advanced Configuration

### Custom Load Profiles

Add your own load profile to config:

```json
"load_profiles": {
  "custom_peak": {
    "operations": {
      "num_calls": {"min": 80, "max": 120},
      "threads": {"min": 15, "max": 20},
      "delay": {"min": 0.2, "max": 0.4}
    }
  }
}
```

### Time-based Profiles

Modify `get_load_profile()` in `simulation_daemon.py` to implement:
- Lunch hour surge (12PM-1PM)
- End-of-day spike (5PM-6PM)
- Weekly patterns (Monday busy, Friday quiet)
- Monthly patterns (month-end busy)

### Custom Metrics

Add custom metrics tracking:
```python
def record_custom_metric(self, metric_name, value):
    # Add to daily summary
    self.custom_metrics[metric_name] = value
```

## Security Considerations

### Guardrail Testing
- Daemon runs security tests automatically
- All tests are logged for audit trail
- Block rates tracked in daily summaries
- Review failed guardrails regularly

### Credentials
- Uses Azure DefaultAzureCredential
- Requires `az login` or service principal
- Credentials never logged or stored
- Follows Azure security best practices

### Access Control
- Daemon runs as user 'azureuser'
- Log files readable only by user/group
- PID file prevents multiple instances
- Graceful shutdown prevents data corruption

## Support and Maintenance

### Regular Tasks
- **Daily**: Review daily summary for target metrics
- **Weekly**: Check error logs, review guardrail results
- **Monthly**: Analyze trends, optimize configuration

### Log Rotation
Set up logrotate:

```bash
# /etc/logrotate.d/simulation-daemon
/home/azureuser/code/AI-Foundry-Agent-Simulation/daemon_results/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

### Backup
Important files to backup:
- Configuration: `simulation_daemon_config.json`
- Daily summaries: `daemon_results/daily_summaries/`
- Metrics (optional): CSV files in `daemon_results/`

## FAQ

**Q: Can I run multiple daemons?**
A: Yes, use different config files and base directories for each instance.

**Q: How do I change the busy hours?**
A: Edit `busy_hours` section in `simulation_daemon_config.json` and restart daemon.

**Q: What if I want more than 5000 requests/day?**
A: Reduce `execution_interval_minutes` or increase per-execution request counts.

**Q: Can I prioritize guardrail testing?**
A: Yes, adjust `simulation_mix` weights in config (e.g., 40% operations, 60% guardrails).

**Q: How do I stop the daemon for maintenance?**
A: Use `./daemon_manager.sh stop` - it will finish current operation and shutdown gracefully.

**Q: What happens if Azure services are down?**
A: Daemon will log errors, enter cooldown after repeated failures, and auto-resume when service recovers.

## Version History

- **v1.0** (2026-01-06): Initial release with basic functionality
  - 24/7 continuous operation
  - Busy/normal/quiet hour profiles
  - Automatic daily summaries
  - Graceful error handling

---

For questions or issues, check the logs first, then review this README.
