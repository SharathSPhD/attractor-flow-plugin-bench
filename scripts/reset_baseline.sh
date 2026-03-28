#!/bin/bash
set -e
PROJ=/Users/sharath/Library/CloudStorage/OneDrive-Personal/wsl_projects/atprove
cp -r "$PROJ/target_pipeline_original/." "$PROJ/target_pipeline/"
# Fix imports: target_pipeline_original -> target_pipeline
find "$PROJ/target_pipeline" -name "*.py" -exec sed -i '' 's/target_pipeline_original/target_pipeline/g' {} +
find "$PROJ/target_pipeline" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$PROJ/target_pipeline" -name "*.pyc" -delete 2>/dev/null || true
rm -f "$PROJ/target_pipeline/pipeline.db"
echo "Baseline reset complete."
