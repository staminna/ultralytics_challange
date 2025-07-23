# 🔄 Git Workflow Commands

## **Step-by-Step Git Commands to Execute**

### **1. Check Current Status**
```bash
git status
git branch --show-current
```

### **2. Stage and Commit Current Changes**
```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "feat: Complete project cleanup and YOLO pipeline implementation

- Updated comprehensive .gitignore with organized sections
- Fixed Pydantic model warnings in API routes  
- Successfully implemented YOLO pipeline with labeled image output
- Processed 264 images (COCO8 + COCO128) with 1,229 detections
- Organized project structure (scripts/, tests/, utils/legacy/)
- Merged all requirements.txt files into single comprehensive file
- Created installation and documentation files
- Fixed pandas/numpy compatibility issues"
```

### **3. Merge with Main Branch**
```bash
# Fetch latest from remote
git fetch origin

# Switch to main branch (create if doesn't exist)
git checkout main || git checkout -b main

# Pull latest main (if remote exists)
git pull origin main || echo "No remote main branch"

# Merge your work into main (replace 'your-branch' with actual branch name)
git merge your-branch --no-ff -m "Merge: Complete YOLO pipeline implementation"

# Push main branch
git push origin main
```

### **4. Create New Branch for End-to-End Pipeline**
```bash
# Create and switch to new branch
git checkout -b feature/end-to-end-pipeline

# Push new branch to remote
git push -u origin feature/end-to-end-pipeline
```

## **🚀 Ready to Run End-to-End Pipeline**

Once you're on the new branch, you can run:

### **Option 1: Automated Pipeline**
```bash
python end_to_end_pipeline.py
```

### **Option 2: Manual Steps**
```bash
# 1. Start server
python backend/start_server.py

# 2. In another terminal, run pipeline
python backend/run_pipeline.py

# 3. Check results
ls -la backend/pipeline_output/
```

## **📋 What the Pipeline Does**

1. **Server Setup**: Starts FastAPI server on port 8000
2. **Dataset Processing**: Processes COCO8 and COCO128 datasets
3. **YOLO Inference**: Runs object detection on all images
4. **Labeled Output**: Creates images with bounding boxes and labels
5. **Results Export**: Saves JSON summaries and labeled images

## **📊 Expected Results**

- **Total Images**: 264 (8 from COCO8 + 256 from COCO128)
- **Total Detections**: ~1,229 objects detected
- **Output Location**: `backend/pipeline_output/` or `end_to_end_output/`
- **File Types**: Original images, labeled images, JSON summaries

## **🔧 Troubleshooting**

If git commands fail:
```bash
# Check git status
git status --porcelain

# Check current branch
cat .git/HEAD

# Check remote connections
git remote -v

# Force add if needed
git add --force .
```

---

✅ **Follow these commands in order to complete the git workflow and run the end-to-end pipeline!**
