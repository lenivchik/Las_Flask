#!/bin/bash

# LAS Validator Docker Setup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed."
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p uploads logs ssl
    
    # Create .gitkeep files to preserve directory structure
    touch uploads/.gitkeep
    touch logs/.gitkeep
    
    print_status "Directories created successfully."
}

# Set permissions
set_permissions() {
    print_status "Setting proper permissions..."
    
    # Make sure upload directory is writable
    chmod 755 uploads
    chmod 755 logs
    
    # Make setup script executable
    chmod +x setup.sh
    
    print_status "Permissions set successfully."
}

# Check if Poetry and lascheck are available
check_poetry() {
    print_status "Checking Poetry and local lascheck..."
    
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
        
        if ! command -v poetry &> /dev/null; then
            print_error "Failed to install Poetry. Please install it manually."
            print_info "Visit: https://python-poetry.org/docs/#installation"
            exit 1
        fi
    fi
    
    # Check if lascheck directory exists
    if [ ! -d "lascheck" ]; then
        print_warning "Local lascheck directory not found."
        print_info "Please ensure you have the lascheck package in the 'lascheck/' directory"
        print_info "Structure should be:"
        print_info "  ."
        print_info "  ├── lascheck/"
        print_info "  │   ├── __init__.py"
        print_info "  │   ├── ..."
        print_info "  └── pyproject.toml"
        
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_status "✅ Local lascheck directory found."
    fi
    
    print_status "Poetry setup complete."
}

# Create Poetry configuration
setup_poetry() {
    print_status "Setting up Poetry configuration..."
    
    # Create poetry.lock if it doesn't exist
    if [ ! -f "poetry.lock" ]; then
        print_status "Creating poetry.lock..."
        poetry lock
    fi
    
    print_status "Poetry configuration ready."
}

# Build and start the application
build_and_start() {
    print_status "Building Docker images..."
    docker-compose build
    
    print_status "Starting LAS Validator application..."
    docker-compose up -d
    
    # Wait a moment for services to start
    sleep 10
    
    # Check if services are running
    print_status "Checking service health..."
    
    if curl -f -s http://localhost:5000/api/health > /dev/null 2>&1; then
        print_status "✅ Flask application is running!"
    else
        print_warning "⚠️  Flask application might not be ready yet. Check logs with: docker-compose logs las-validator"
    fi
    
    if curl -f -s http://localhost/ > /dev/null 2>&1; then
        print_status "✅ Nginx proxy is running!"
    else
        print_warning "⚠️  Nginx might not be ready yet. Check logs with: docker-compose logs nginx"
    fi
}

# Show final information
show_info() {
    print_info ""
    print_info "🎉 LAS Validator setup complete!"
    print_info ""
    print_info "Access your application at:"
    print_info "  • Main application: http://localhost"
    print_info "  • Direct Flask app: http://localhost:5000"
    print_info "  • Health check: http://localhost:5000/api/health"
    print_info ""
    print_info "Useful commands:"
    print_info "  • View logs: docker-compose logs -f"
    print_info "  • Stop app: docker-compose down"
    print_info "  • Restart: docker-compose restart"
    print_info "  • Or use: make help"
    print_info ""
}

# Main setup function
main() {
    echo -e "${BLUE}"
    echo "================================================="
    echo "    LAS Validator Docker Setup (Poetry)"
    echo "================================================="
    echo -e "${NC}"
    
    check_docker
    check_poetry
    create_directories
    set_permissions
    setup_poetry
    build_and_start
    show_info
}

# Handle script arguments
case "${1:-setup}" in
    "setup"|"")
        main
        ;;
    "clean")
        print_status "Cleaning up Docker containers and images..."
        docker-compose down --rmi all --volumes --remove-orphans || true
        docker system prune -f || true
        print_status "Cleanup complete!"
        ;;
    "rebuild")
        print_status "Rebuilding application..."
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        print_status "Rebuild complete!"
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        ;;
    *)
        echo "Usage: $0 [setup|clean|rebuild|logs|status]"
        echo ""
        echo "Commands:"
        echo "  setup    - Initial setup (default)"
        echo "  clean    - Clean up containers and images"
        echo "  rebuild  - Rebuild and restart"
        echo "  logs     - Show logs"
        echo "  status   - Show container status"
        exit 1
        ;;
esac