# GitHub Repository Setup Guide

This guide will help you push your StatBox project to GitHub.

## 🚨 Important: Before Pushing

Make sure you **NEVER** commit:
- `.env` files (contains secrets)
- `db.sqlite3` (database file)
- SSH keys (`.pub`, `*_rsa` files)
- SSL certificates
- Media files (user uploads)

All these are now excluded by `.gitignore`.

---

## Step 1: Clean Up Your Repository

Your repository currently has many files staged that shouldn't be committed. Let's clean it up:

```bash
# Remove all files from staging
git reset

# Add .gitignore first
git add .gitignore

# Commit .gitignore
git commit -m "Add .gitignore file"
```

## Step 2: Add Your Project Files

```bash
# Add all appropriate files (respects .gitignore)
git add .

# Check what will be committed (make sure no sensitive files!)
git status

# If you see sensitive files, remove them:
# git rm --cached <filename>
```

## Step 3: Create Your First Commit

```bash
# Make your initial commit
git commit -m "Initial commit: StatBox application

- Django application with statistical analysis features
- User authentication and subscription management
- Docker deployment configuration
- DigitalOcean deployment guides"
```

## Step 4: Create a GitHub Repository

### Option A: Using GitHub Website

1. **Go to GitHub**: https://github.com
2. **Log in** to your account (or create one if needed)
3. **Click the "+" icon** in the top right → "New repository"
4. **Fill in repository details**:
   - Repository name: `statbox` (or your preferred name)
   - Description: "Statistical analysis web application built with Django"
   - Visibility: Choose **Private** (recommended for production apps) or Public
   - **DO NOT** initialize with README, .gitignore, or license (you already have these)
5. **Click "Create repository"**

### Option B: Using GitHub CLI (if installed)

```bash
# Install GitHub CLI (if not installed)
# macOS: brew install gh
# Then authenticate: gh auth login

# Create repository
gh repo create statbox --private --source=. --remote=origin --push
```

## Step 5: Connect Local Repository to GitHub

After creating the repository on GitHub, you'll see instructions. Use these commands:

```bash
# Add GitHub as remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/statbox.git

# Or if using SSH (requires SSH key setup):
# git remote add origin git@github.com:YOUR_USERNAME/statbox.git

# Verify remote was added
git remote -v
```

## Step 6: Push to GitHub

```bash
# Push your code to GitHub
git push -u origin main

# If you get an error about branch name, try:
# git branch -M main
# git push -u origin main
```

## Step 7: Verify Upload

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/statbox`
2. You should see all your files (except those in `.gitignore`)
3. Verify that sensitive files like `.env`, `db.sqlite3` are NOT visible

---

## 🔐 Security Checklist

Before pushing, verify:

- [ ] `.env` file is NOT in repository
- [ ] `db.sqlite3` is NOT in repository
- [ ] No SSH keys (`.pub`, `*_rsa`) in repository
- [ ] No SSL certificates (`.pem`, `.key`) in repository
- [ ] `__pycache__/` directories are ignored
- [ ] `.DS_Store` files are ignored
- [ ] `media/` directory is ignored (or only example files committed)
- [ ] `staticfiles/` directory is ignored

---

## 🚀 Quick Commands Reference

### Initial Setup (First Time)

```bash
# 1. Clean staging area
git reset

# 2. Add .gitignore and commit
git add .gitignore
git commit -m "Add .gitignore"

# 3. Add all files (respects .gitignore)
git add .
git commit -m "Initial commit"

# 4. Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/statbox.git

# 5. Push to GitHub
git push -u origin main
```

### Regular Updates

```bash
# After making changes
git add .
git commit -m "Description of changes"
git push
```

### Pull Latest Changes

```bash
# If working from multiple machines
git pull origin main
```

---

## 📝 Next Steps After Pushing

1. **Add a README.md** (if you haven't already):
   ```bash
   # Create README.md with project description
   # Then commit and push
   git add README.md
   git commit -m "Add README"
   git push
   ```

2. **Update DigitalOcean Deployment Guide**:
   - In `DIGITALOCEAN_DEPLOYMENT.md`, update the clone command with your actual GitHub URL

3. **Set up branch protection** (optional):
   - Go to Settings → Branches
   - Add rule for `main` branch
   - Require pull request reviews before merging

4. **Add collaborators** (if needed):
   - Settings → Collaborators → Add people

---

## 🔄 If You Need to Remove Files Already Committed

If you accidentally committed sensitive files:

```bash
# Remove file from Git (but keep locally)
git rm --cached .env
git rm --cached db.sqlite3

# Commit the removal
git commit -m "Remove sensitive files"

# Push changes
git push

# IMPORTANT: If files were already pushed, they're in Git history
# You may need to:
# 1. Regenerate any exposed secrets
# 2. Consider using git-filter-repo to clean history (advanced)
```

---

## ❓ Troubleshooting

### "Remote origin already exists"
```bash
# Remove existing remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/YOUR_USERNAME/statbox.git
```

### "Authentication failed"
- Use Personal Access Token instead of password:
  1. GitHub → Settings → Developer settings → Personal access tokens
  2. Generate new token (classic)
  3. Select scopes: `repo` (full control)
  4. Use token as password when pushing

### "Branch main does not exist"
```bash
# Rename current branch to main
git branch -M main

# Or create main branch
git checkout -b main
```

---

## 🎉 You're All Set!

Your code is now on GitHub and you can:
- Deploy from GitHub to your DigitalOcean server
- Collaborate with others
- Track changes and versions
- Use GitHub Actions for CI/CD (optional)

**Remember**: Never commit secrets or sensitive data!

