#!/bin/bash

# Fix missing linearmodels package

echo "🔧 Fixing missing linearmodels package..."
echo ""

cd ~/GRA || { echo "❌ Not in GRA directory"; exit 1; }

echo "Option 1: Quick fix - Install in running container (temporary)"
echo "=============================================================="
echo ""
read -p "Install linearmodels in running container? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing linearmodels in web container..."
    docker-compose exec -T web pip install linearmodels>=5.0.0 || \
    docker-compose run --rm web pip install linearmodels>=5.0.0
    
    echo "Restarting web container..."
    docker-compose restart web
    echo "✅ linearmodels installed (temporary - will be lost on rebuild)"
fi

echo ""
echo "Option 2: Permanent fix - Rebuild container (recommended)"
echo "========================================================="
echo ""
echo "The linearmodels package needs to be added to requirements-prod.txt"
echo "and the container needs to be rebuilt."
echo ""
read -p "Add linearmodels to requirements-prod.txt and rebuild? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if it's already in requirements-prod.txt
    if grep -q "linearmodels" requirements-prod.txt; then
        echo "✅ linearmodels already in requirements-prod.txt"
    else
        echo "Adding linearmodels to requirements-prod.txt..."
        # Add after statsmodels
        sed -i '/statsmodels>=0.14.2/a linearmodels>=5.0.0' requirements-prod.txt
        echo "✅ Added to requirements-prod.txt"
    fi
    
    echo ""
    echo "Rebuilding web container..."
    docker-compose build web
    
    echo ""
    echo "Restarting web container..."
    docker-compose restart web
    
    echo ""
    echo "✅ Container rebuilt with linearmodels (permanent fix)"
fi

echo ""
echo "Verifying installation..."
sleep 3
docker-compose exec -T web python -c "import linearmodels; print(f'✅ linearmodels version: {linearmodels.__version__}')" 2>&1 || \
docker-compose run --rm web python -c "import linearmodels; print(f'✅ linearmodels version: {linearmodels.__version__}')" 2>&1

echo ""
echo "📋 Summary:"
echo "==========="
echo "Option 1: Quick fix (temporary) - installs in running container"
echo "Option 2: Permanent fix - adds to requirements-prod.txt and rebuilds"
echo ""
echo "For production, use Option 2 to ensure the package persists."
