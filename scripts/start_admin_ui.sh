#!/usr/bin/env bash

# Admin UI Startup Script
# Handles environment setup, dependencies, process management, and launches the admin UI

set -e  # Exit on any error

# Configuration
ADMIN_UI_PORT=3500
BACKEND_PORT=4500
ADMIN_UI_DIR="apps/admin-ui"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/README.md" ]] || [[ ! -d "$PROJECT_ROOT/apps" ]]; then
        log_error "This script must be run from the mumbl-language-system project root"
        log_error "Current directory: $(pwd)"
        log_error "Expected project root: $PROJECT_ROOT"
        exit 1
    fi
}

# Kill existing processes on our ports
kill_existing_processes() {
    log_info "Checking for existing processes on ports $ADMIN_UI_PORT and $BACKEND_PORT..."
    
    # Kill processes on admin UI port
    if lsof -ti:$ADMIN_UI_PORT > /dev/null 2>&1; then
        log_warning "Found process on port $ADMIN_UI_PORT, killing it..."
        lsof -ti:$ADMIN_UI_PORT | xargs kill -9
        sleep 1
    fi
    
    # Kill processes on backend port
    if lsof -ti:$BACKEND_PORT > /dev/null 2>&1; then
        log_warning "Found process on port $BACKEND_PORT, killing it..."
        lsof -ti:$BACKEND_PORT | xargs kill -9
        sleep 1
    fi
    
    log_success "Port cleanup complete"
}

# Check and install Node.js dependencies
setup_node_dependencies() {
    log_info "Setting up Node.js dependencies..."
    
    cd "$PROJECT_ROOT/$ADMIN_UI_DIR"
    
    # Check if node_modules exists and is recent
    if [[ ! -d "node_modules" ]] || [[ ! -f "node_modules/.package-lock.json" ]]; then
        log_info "Installing npm dependencies..."
        npm install
    else
        log_info "Checking for npm dependency updates..."
        npm install
    fi
    
    cd "$PROJECT_ROOT"
    log_success "Node.js dependencies ready"
}

# Check and setup Python environment
setup_python_environment() {
    log_info "Setting up Python environment..."
    
    # Check if virtual environment exists
    if [[ ! -d ".venv" ]]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install/update Python dependencies
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r packages/data-contracts/python/requirements.txt
    
    # Install data contracts package in development mode
    log_info "Installing data contracts package..."
    pip install -e packages/data-contracts/python/
    
    log_success "Python environment ready"
}

# Create environment files
create_env_files() {
    log_info "Setting up environment files..."
    
    # Admin UI environment
    if [[ ! -f "$ADMIN_UI_DIR/.env" ]]; then
        log_info "Creating admin UI .env file..."
        cat > "$ADMIN_UI_DIR/.env" << EOF
# Admin UI Environment Configuration
VITE_API_URL=http://localhost:$BACKEND_PORT
VITE_APP_NAME=Mumbl Admin
VITE_APP_VERSION=0.1.0
VITE_DEV_MODE=true
EOF
        log_success "Created $ADMIN_UI_DIR/.env"
    fi
    
    # Backend environment (placeholder for future)
    if [[ ! -f "apps/runtime/.env" ]]; then
        log_info "Creating backend .env file..."
        cat > "apps/runtime/.env" << EOF
# Backend Environment Configuration
PORT=$BACKEND_PORT
NODE_ENV=development
DATABASE_URL=postgres://user:pass@localhost:5432/mumbl
STORAGE_BUCKET=mumbl-dev
ASR_PROVIDER=whisper
EOF
        log_success "Created apps/runtime/.env"
    fi
    
    # Project root environment
    if [[ ! -f ".env" ]]; then
        log_info "Creating project root .env file..."
        cat > ".env" << EOF
# Project Environment Configuration
ADMIN_UI_PORT=$ADMIN_UI_PORT
BACKEND_PORT=$BACKEND_PORT
PYTHON_VERSION=3.9+
NODE_VERSION=20+
EOF
        log_success "Created project .env"
    fi
}

# Build TypeScript contracts (if needed)
build_contracts() {
    log_info "Building TypeScript contracts..."
    
    cd "$PROJECT_ROOT/packages/data-contracts/typescript"
    
    # Check if build is needed
    if [[ ! -d "dist" ]] || [[ "src" -nt "dist" ]]; then
        log_info "Building TypeScript contracts..."
        npm run build
    else
        log_info "TypeScript contracts already built"
    fi
    
    cd "$PROJECT_ROOT"
    log_success "TypeScript contracts ready"
}

# Generate schemas and types (if needed)
generate_schemas() {
    log_info "Generating schemas and types..."
    
    # Activate Python environment
    source .venv/bin/activate
    
    # Generate JSON schemas
    if [[ ! -d "packages/data-contracts/typescript/schemas" ]] || \
       [[ "packages/data-contracts/python/src" -nt "packages/data-contracts/typescript/schemas" ]]; then
        log_info "Generating JSON schemas..."
        python scripts/generate_schemas.py
    fi
    
    # Generate TypeScript types
    if [[ ! -d "packages/data-contracts/typescript/src" ]] || \
       [[ "packages/data-contracts/typescript/schemas" -nt "packages/data-contracts/typescript/src" ]]; then
        log_info "Generating TypeScript types..."
        python scripts/generate_typescript_types.py
    fi
    
    log_success "Schemas and types ready"
}

# Open browser function
open_browser() {
    local url="http://localhost:$ADMIN_UI_PORT"
    log_info "Opening browser to $url..."
    
    # Wait a moment for the server to start
    sleep 3
    
    # Try to open browser based on OS
    if command -v open >/dev/null 2>&1; then
        # macOS
        open "$url"
    elif command -v xdg-open >/dev/null 2>&1; then
        # Linux
        xdg-open "$url"
    elif command -v start >/dev/null 2>&1; then
        # Windows
        start "$url"
    else
        log_warning "Could not automatically open browser. Please visit: $url"
    fi
}

# Start the admin UI
start_admin_ui() {
    log_info "Starting admin UI on port $ADMIN_UI_PORT..."
    
    cd "$PROJECT_ROOT/$ADMIN_UI_DIR"
    
    # Start the development server in background and open browser
    log_success "Launching admin UI..."
    log_info "Admin UI will be available at: http://localhost:$ADMIN_UI_PORT"
    log_info "Press Ctrl+C to stop the server"
    
    # Start the dev server and open browser
    npm run dev -- --port $ADMIN_UI_PORT --host 0.0.0.0 &
    local server_pid=$!
    
    # Store the PID for cleanup
    echo $server_pid > /tmp/mumbl_admin_ui.pid
    
    # Open browser after a short delay
    open_browser
    
    # Wait for the server process
    wait $server_pid
}

# Main execution
main() {
    log_info "Starting Mumbl Admin UI..."
    log_info "Project root: $PROJECT_ROOT"
    
    # Check we're in the right place
    check_project_root
    
    # Setup steps
    kill_existing_processes
    setup_python_environment
    setup_node_dependencies
    create_env_files
    build_contracts
    generate_schemas
    
    # Start the application
    start_admin_ui
}

# Handle script interruption
cleanup() {
    log_warning "Shutting down..."
    
    # Kill any processes we started
    if lsof -ti:$ADMIN_UI_PORT > /dev/null 2>&1; then
        lsof -ti:$ADMIN_UI_PORT | xargs kill -9
    fi
    
    # Clean up PID file
    if [[ -f "/tmp/mumbl_admin_ui.pid" ]]; then
        rm -f /tmp/mumbl_admin_ui.pid
    fi
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function
main "$@"
