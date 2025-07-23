#!/bin/bash
# Git Workflow: Merge with main and create end-to-end pipeline branch

set -e  # Exit on any error

echo "🔄 Git Workflow: Merge with main and create pipeline branch"
echo "============================================================"

# Step 1: Check current status
echo "📋 Step 1: Checking current git status..."
git status --porcelain

# Step 2: Check current branch
echo "🌿 Step 2: Checking current branch..."
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

# Step 3: Stage all changes
echo "📦 Step 3: Staging all changes..."
git add .

# Step 4: Commit current changes
echo "💾 Step 4: Committing current changes..."
git commit -m "feat: Complete project cleanup and YOLO pipeline implementation

- Updated comprehensive .gitignore with organized sections
- Fixed Pydantic model warnings in API routes
- Successfully implemented YOLO pipeline with labeled image output
- Processed 264 images (COCO8 + COCO128) with 1,229 detections
- Organized project structure (scripts/, tests/, utils/legacy/)
- Merged all requirements.txt files into single comprehensive file
- Created installation and documentation files
- Fixed pandas/numpy compatibility issues"

# Step 5: Fetch latest from remote
echo "🔄 Step 5: Fetching latest from remote..."
git fetch origin

# Step 6: Switch to main branch
echo "🌿 Step 6: Switching to main branch..."
git checkout main || git checkout -b main

# Step 7: Pull latest main
echo "⬇️  Step 7: Pulling latest main..."
git pull origin main || echo "No remote main branch or already up to date"

# Step 8: Merge current work into main
echo "🔀 Step 8: Merging work into main..."
if [ "$CURRENT_BRANCH" != "main" ]; then
    git merge $CURRENT_BRANCH --no-ff -m "Merge branch '$CURRENT_BRANCH' - Complete YOLO pipeline implementation"
fi

# Step 9: Push main
echo "⬆️  Step 9: Pushing main branch..."
git push origin main

# Step 10: Create new branch for end-to-end pipeline
echo "🆕 Step 10: Creating end-to-end pipeline branch..."
PIPELINE_BRANCH="feature/end-to-end-pipeline"
git checkout -b $PIPELINE_BRANCH

# Step 11: Push new branch
echo "⬆️  Step 11: Pushing new pipeline branch..."
git push -u origin $PIPELINE_BRANCH

echo ""
echo "✅ Git workflow completed successfully!"
echo "📋 Summary:"
echo "  - Merged changes into main branch"
echo "  - Created new branch: $PIPELINE_BRANCH"
echo "  - Ready for end-to-end pipeline development"
echo ""
echo "🚀 Next steps:"
echo "  1. Run the YOLO pipeline: python backend/run_pipeline.py"
echo "  2. Start the server: python backend/start_server.py"
echo "  3. Test the complete workflow"
