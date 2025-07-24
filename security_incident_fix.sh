#!/bin/bash

# SECURITY INCIDENT: Remove service-account-key.json from Git History
# This script removes sensitive credentials from git history

set -e  # Exit on any error

echo "🚨 SECURITY INCIDENT: Removing service-account-key.json from Git History"
echo "============================================================================"
echo ""

# Check if file exists in current working directory
if [ -f "service-account-key.json" ]; then
    echo "⚠️  WARNING: service-account-key.json found in working directory"
    echo "📁 File will be moved to secure location after git cleanup"
else
    echo "ℹ️  service-account-key.json not in working directory (good)"
fi

echo ""
echo "🔍 Checking git status..."
git status --porcelain

echo ""
read -p "❓ Do you want to stash current changes? (y/n): " stash_changes
if [ "$stash_changes" = "y" ]; then
    echo "📦 Stashing current changes..."
    git stash push -m "Security fix: stashing before credential cleanup"
fi

echo ""
echo "🗑️  Removing service-account-key.json from git history..."
echo "⚠️  This will rewrite git history - make sure your team is aware!"
echo ""
read -p "❓ Continue with history rewrite? (y/n): " continue_rewrite

if [ "$continue_rewrite" != "y" ]; then
    echo "❌ Aborted by user"
    exit 1
fi

# Set filter-branch warning suppression
export FILTER_BRANCH_SQUELCH_WARNING=1

echo "🔧 Running git filter-branch..."
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch service-account-key.json' \
  --prune-empty --tag-name-filter cat -- --all

echo "🧹 Cleaning up git references..."
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "✅ Git history cleanup complete!"

# Verify removal
echo "🔍 Verifying removal from git history..."
if git log --all --full-history -- service-account-key.json | grep -q commit; then
    echo "❌ ERROR: File still found in git history!"
    exit 1
else
    echo "✅ File successfully removed from git history"
fi

# Secure the credentials if file exists
if [ -f "service-account-key.json" ]; then
    echo ""
    echo "🔒 Securing credentials..."
    ./secure_credentials.sh
fi

# Restore stashed changes if any
if [ "$stash_changes" = "y" ]; then
    echo ""
    echo "📦 Restoring stashed changes..."
    git stash pop
fi

echo ""
echo "🎉 SECURITY INCIDENT RESOLVED!"
echo "============================================================================"
echo "📋 NEXT STEPS:"
echo "   1. 🔄 ROTATE the service account key in Google Cloud Console"
echo "   2. 📤 Force push to remote: git push origin --force --all"
echo "   3. 👥 Notify your team about the history rewrite"
echo "   4. 🧪 Test that credentials still work: python test_environment.py"
echo ""
echo "⚠️  IMPORTANT: The old key is now considered compromised!"
echo "🔑 Create a new service account key in Google Cloud Console"
echo ""
