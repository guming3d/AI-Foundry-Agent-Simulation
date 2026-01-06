#!/bin/bash
#
# Daemon Manager for AI Foundry Agent Simulation
# Provides start, stop, restart, and status commands
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_SCRIPT="$SCRIPT_DIR/simulation_daemon.py"
PID_FILE="$SCRIPT_DIR/daemon_results/daemon.pid"
LOG_DIR="$SCRIPT_DIR/daemon_results"
PYTHON="${SCRIPT_DIR}/.venv/bin/python3"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$LOG_DIR"

function print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function check_python() {
    if [ ! -f "$PYTHON" ]; then
        print_error "Python virtual environment not found at $PYTHON"
        print_error "Please create virtual environment: python3 -m venv .venv"
        exit 1
    fi
}

function get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

function is_running() {
    local pid=$(get_pid)
    if [ -z "$pid" ]; then
        return 1
    fi

    if ps -p "$pid" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

function start_daemon() {
    print_status "Starting simulation daemon..."

    check_python

    if is_running; then
        print_warning "Daemon is already running (PID: $(get_pid))"
        return 1
    fi

    # Remove stale PID file
    if [ -f "$PID_FILE" ]; then
        rm "$PID_FILE"
    fi

    # Start daemon in background
    nohup "$PYTHON" "$DAEMON_SCRIPT" \
        > "$LOG_DIR/daemon_stdout.log" \
        2> "$LOG_DIR/daemon_stderr.log" &

    local pid=$!
    echo $pid > "$PID_FILE"

    # Wait a moment and check if it's still running
    sleep 2
    if is_running; then
        print_status "Daemon started successfully (PID: $pid)"
        print_status "Logs: $LOG_DIR/simulation_daemon.log"
        print_status "Use 'tail -f $LOG_DIR/simulation_daemon.log' to monitor"
        return 0
    else
        print_error "Daemon failed to start. Check logs at:"
        print_error "  $LOG_DIR/daemon_stderr.log"
        rm -f "$PID_FILE"
        return 1
    fi
}

function stop_daemon() {
    print_status "Stopping simulation daemon..."

    if ! is_running; then
        print_warning "Daemon is not running"
        rm -f "$PID_FILE"
        return 1
    fi

    local pid=$(get_pid)
    print_status "Sending SIGTERM to PID $pid..."

    # Send SIGTERM for graceful shutdown
    kill -TERM "$pid" 2>/dev/null

    # Wait up to 30 seconds for graceful shutdown
    local count=0
    while [ $count -lt 30 ]; do
        if ! is_running; then
            print_status "Daemon stopped gracefully"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done

    # Force kill if still running
    print_warning "Daemon did not stop gracefully, forcing..."
    kill -KILL "$pid" 2>/dev/null
    sleep 1

    if ! is_running; then
        print_status "Daemon forcefully stopped"
        rm -f "$PID_FILE"
        return 0
    else
        print_error "Failed to stop daemon"
        return 1
    fi
}

function restart_daemon() {
    print_status "Restarting simulation daemon..."
    stop_daemon
    sleep 2
    start_daemon
}

function status_daemon() {
    echo "========================================="
    echo "Simulation Daemon Status"
    echo "========================================="

    if is_running; then
        local pid=$(get_pid)
        echo -e "Status: ${GREEN}RUNNING${NC}"
        echo "PID: $pid"

        # Show process info
        echo ""
        echo "Process Info:"
        ps -p "$pid" -o pid,ppid,etime,pcpu,pmem,cmd --no-headers

        # Show recent log entries
        if [ -f "$LOG_DIR/simulation_daemon.log" ]; then
            echo ""
            echo "Recent Log Entries (last 10 lines):"
            echo "---"
            tail -10 "$LOG_DIR/simulation_daemon.log"
        fi

        # Show today's totals if available
        echo ""
        echo "Log Files:"
        echo "  Main log: $LOG_DIR/simulation_daemon.log"
        echo "  Stdout: $LOG_DIR/daemon_stdout.log"
        echo "  Stderr: $LOG_DIR/daemon_stderr.log"
    else
        echo -e "Status: ${RED}STOPPED${NC}"
        if [ -f "$PID_FILE" ]; then
            print_warning "Stale PID file found: $PID_FILE"
        fi
    fi

    echo ""
    echo "Configuration: $SCRIPT_DIR/simulation_daemon_config.json"
    echo "========================================="
}

function show_logs() {
    if [ ! -f "$LOG_DIR/simulation_daemon.log" ]; then
        print_error "Log file not found: $LOG_DIR/simulation_daemon.log"
        return 1
    fi

    tail -f "$LOG_DIR/simulation_daemon.log"
}

function show_help() {
    cat << EOF
Daemon Manager for AI Foundry Agent Simulation

Usage: $0 [COMMAND]

Commands:
    start       Start the daemon
    stop        Stop the daemon
    restart     Restart the daemon
    status      Show daemon status and recent logs
    logs        Tail the daemon log file (Ctrl+C to exit)
    help        Show this help message

Examples:
    $0 start
    $0 stop
    $0 status
    $0 logs

Files:
    Daemon script: $DAEMON_SCRIPT
    PID file:      $PID_FILE
    Log directory: $LOG_DIR

EOF
}

# Main command dispatcher
case "${1:-}" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        restart_daemon
        ;;
    status)
        status_daemon
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Invalid command: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac
