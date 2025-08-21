#!/usr/bin/env bash

# Stop Admin UI Script
# Kills any running admin UI processes

set -e

# Configuration
ADMIN_UI_PORT=3500
BACKEND_PORT=4500

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Kill processes on specified ports
kill_port_processes() {
    local port=$1
    local service_name=$2
    
    if lsof -ti:$port > /dev/null 2>&1; then
        log_info "Stopping $service_name on port $port..."
        lsof -ti:$port | xargs kill -9
        log_success "Stopped $service_name"
    else
        log_info "No $service_name process found on port $port"
    fi
}

# Clean up PID file
cleanup_pid_file() {
    if [[ -f "/tmp/mumbl_admin_ui.pid" ]]; then
        log_info "Cleaning up PID file..."
        rm -f /tmp/mumbl_admin_ui.pid
        log_success "PID file cleaned up"
    fi
}

# Main execution
main() {
    log_info "Stopping Mumbl Admin UI..."
    
    # Kill processes on our ports
    kill_port_processes $ADMIN_UI_PORT "Admin UI"
    kill_port_processes $BACKEND_PORT "Backend"
    
    # Clean up PID file
    cleanup_pid_file
    
    log_success "All Mumbl processes stopped"
}

# Run main function
main "$@"
