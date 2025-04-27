#!/bin/bash
set -e

# Load credentials
if [ -f ".env" ]; then
  source .env
  echo "Loaded credentials from .env file"
else
  echo "Error: .env file not found"
  exit 1
fi

# Verify credentials
if [ -z "$GH_REPO" ] || [ -z "$GH_TOKEN" ]; then
  echo "Error: GH_REPO or GH_TOKEN not set in .env file"
  exit 1
fi

# Clean repo name
CLEAN_REPO=$(echo "$GH_REPO" | sed 's|^https://github.com/||')
REPO_URL="https://$GH_TOKEN@github.com/$CLEAN_REPO"

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Working in temporary directory: $TEMP_DIR"

# Clone the existing repository
echo "Cloning repository..."
git clone "$REPO_URL" "$TEMP_DIR"

# Create .gitignore if it doesn't exist
if [ ! -f "$TEMP_DIR/.gitignore" ]; then
  echo "Creating .gitignore file..."
  cat > "$TEMP_DIR/.gitignore" << "EOF"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
*_env*/

# Environment variables and secrets
.env
*.key
*.pem
*.cert

# OS specific files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs and databases
*.log
*.sqlite
logs/
*.db

# Temporary files
tmp/
temp/
*.tmp
*.swp
*.swo

# Browser cookies
*_cookies.json
EOF
fi

# Copy all files from current directory to the cloned repo
# Excluding .git, .env, and other typical files to ignore
echo "Copying project files..."
rsync -av --exclude='.git/' --exclude='.env' --exclude='__pycache__/' \
  --exclude='*.pyc' --exclude='*.pyo' --exclude='*.pyd' --exclude='.DS_Store' \
  --exclude='venv/' --exclude='*_env*/' --exclude='*.log' --exclude='tmp/' \
  --exclude='temp/' --exclude='*.tmp' \
  ./ "$TEMP_DIR/"

# Commit and push changes
cd "$TEMP_DIR"
echo "Adding files to git..."
git add -A
echo "Committing changes..."
git commit -m "Sync entire project folder" || echo "No changes to commit"
echo "Pushing to repository..."
git push

echo "Successfully updated repository"
cd - > /dev/null
rm -rf "$TEMP_DIR"
