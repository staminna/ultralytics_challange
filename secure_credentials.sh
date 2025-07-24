#!/bin/bash

# Secure Credentials Setup Script
echo "🔒 Securing Google Cloud Service Account Key"

# Create secure credentials directory
CREDS_DIR="$HOME/.config/gcp"
mkdir -p "$CREDS_DIR"

# Move service account key to secure location
if [ -f "service-account-key.json" ]; then
    echo "📁 Moving service-account-key.json to secure location..."
    mv service-account-key.json "$CREDS_DIR/ultralytics-service-account.json"
    chmod 600 "$CREDS_DIR/ultralytics-service-account.json"
    echo "✅ Moved to: $CREDS_DIR/ultralytics-service-account.json"
    echo "🔐 Set secure permissions (600)"
fi

# Update .env file
if [ -f ".env" ]; then
    echo "📝 Updating .env file with secure path..."
    sed -i.bak "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$CREDS_DIR/ultralytics-service-account.json|" .env
    echo "✅ Updated .env file"
fi

# Update .env.example
if [ -f ".env.example" ]; then
    echo "📝 Updating .env.example..."
    sed -i.bak "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcp/ultralytics-service-account.json|" .env.example
    echo "✅ Updated .env.example"
fi

echo ""
echo "🎉 Security Setup Complete!"
echo "📋 Next Steps:"
echo "   1. Run: git add .gitignore .env.example"
echo "   2. Run: git commit -m 'Security: Remove service account key from repo'"
echo "   3. Verify credentials work: python test_environment.py"
echo ""
echo "🔒 Your service account key is now stored securely at:"
echo "   $CREDS_DIR/ultralytics-service-account.json"
