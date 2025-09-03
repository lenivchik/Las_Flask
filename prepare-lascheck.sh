#!/bin/bash

# Script to prepare lascheck directory for Docker build

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Main preparation function
main() {
    print_info "🔧 Preparing lascheck directory for Docker build..."
    print_info ""
    
    # Check current situation
    if [ -d "lascheck" ]; then
        print_status "✅ lascheck directory already exists"
        ls -la lascheck/
    elif [ -d "../lascheck-master" ]; then
        print_status "📁 Found lascheck-master directory, copying to lascheck/"
        cp -r ../lascheck-master ./lascheck
        print_status "✅ Copied lascheck-master to ./lascheck/"
    else
        print_error "❌ Could not find lascheck package!"
        print_info "Please ensure you have one of:"
        print_info "  • ./lascheck/ directory"
        print_info "  • ../lascheck-master/ directory"
        print_info ""
        print_info "Your poetry.lock shows lascheck at '../lascheck-master'"
        exit 1
    fi
    
    # Check lascheck structure
    if [ -f "lascheck/__init__.py" ]; then
        print_status "✅ Found lascheck/__init__.py"
    else
        print_warning "⚠️  No __init__.py found in lascheck/"
    fi
    
    if [ -f "lascheck/pyproject.toml" ]; then
        print_status "✅ Found lascheck/pyproject.toml"
        print_info "lascheck dependencies will be installed with Poetry"
    else
        print_warning "⚠️  No pyproject.toml found in lascheck/"
        print_info "lascheck will be installed with pip"
    fi
    
    # Update poetry.lock if needed
    if [ -f "poetry.lock" ] && grep -q "../lascheck-master" poetry.lock; then
        print_status "📝 Updating poetry.lock to use ./lascheck path..."
        print_info "Regenerating poetry.lock file..."
        poetry lock
        print_status "✅ poetry.lock updated"
    elif [ ! -f "poetry.lock" ]; then
        print_status "📝 Creating poetry.lock file..."
        poetry lock
        print_status "✅ poetry.lock created"
    fi
    
    print_info ""
    print_status "🎉 lascheck preparation complete!"
    print_info "Now you can run: docker-compose build"
}

# Run the main function
main "$@"