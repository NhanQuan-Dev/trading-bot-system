# GitHub Setup Commands

## 📋 Checklist trước khi push lên GitHub

- [ ] Đã tạo repository trên GitHub
- [ ] Đã có file .gitignore
- [ ] Đã có README.md
- [ ] Đã xóa các file nhạy cảm (.env, credentials)
- [ ] Đã test code locally
- [ ] Đã commit tất cả changes

---

## 🚀 Bước 1: Tạo Repository trên GitHub

1. Đăng nhập GitHub
2. Click **"New Repository"**
3. Điền thông tin:
   - Repository name: `trading-bot-platform`
   - Description: "Automated Trading Bot Platform with Backtesting"
   - Visibility: **Private** (recommended) hoặc Public
   - **KHÔNG** check "Initialize with README" (vì đã có local)
4. Click **"Create repository"**

---

## 🔧 Bước 2: Setup Local Repository

### Nếu chưa có Git repo:
```bash
cd /home/qwe/Desktop/zxc

# Initialize git
git init

# Tạo .gitignore (đã có rồi)
# Kiểm tra file không bị track
git status

# Add tất cả files
git add .

# Commit đầu tiên
git commit -m "chore: initial commit - trading bot platform v1.0.0"
```

### Nếu đã có Git repo:
```bash
cd /home/qwe/Desktop/zxc

# Kiểm tra status
git status

# Add changes
git add .

# Commit
git commit -m "chore: add deployment documentation and CI/CD workflows"
```

---

## 🌐 Bước 3: Connect với GitHub Remote

```bash
# Thêm remote origin (thay YOUR_USERNAME và REPO_NAME)
git remote add origin git@github.com:YOUR_USERNAME/trading-bot-platform.git

# Hoặc nếu dùng HTTPS:
# git remote add origin https://github.com/YOUR_USERNAME/trading-bot-platform.git

# Verify remote
git remote -v
```

---

## 🌳 Bước 4: Tạo Branch Structure

```bash
# Đổi tên branch main (nếu đang là master)
git branch -M main

# Push main branch
git push -u origin main

# Tạo develop branch
git checkout -b develop
git push -u origin develop

# Tạo uat branch
git checkout -b uat
git push -u origin uat

# Quay lại develop để làm việc
git checkout develop
```

---

## 🔒 Bước 5: Setup Branch Protection trên GitHub

### Main Branch Protection:
1. Vào GitHub → Settings → Branches
2. Click **"Add rule"**
3. Branch name pattern: `main`
4. Check các options:
   - ✅ Require pull request reviews before merging
     - Required approving reviews: **2**
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators: **NO**
   - ✅ Restrict who can push: Only CI/CD
5. Click **"Create"**

### UAT Branch Protection:
1. Branch name pattern: `uat`
2. Check:
   - ✅ Require pull request reviews: **1**
   - ✅ Require status checks to pass
3. Click **"Create"**

### Develop Branch Protection:
1. Branch name pattern: `develop`
2. Check:
   - ✅ Require status checks to pass
3. Click **"Create"**

---

## 🤖 Bước 6: Setup GitHub Secrets (cho CI/CD)

Vào GitHub → Settings → Secrets and variables → Actions → New repository secret

Thêm các secrets sau:

### Docker Registry (nếu dùng Docker Hub)
```
DOCKER_REGISTRY = docker.io
DOCKER_USERNAME = your-dockerhub-username
DOCKER_PASSWORD = your-dockerhub-password
```

### Server SSH (nếu deploy qua SSH)
```
DEV_SERVER_HOST = dev.your-domain.com
DEV_SERVER_USER = deploy
DEV_SERVER_SSH_KEY = (paste private key)

UAT_SERVER_HOST = uat.your-domain.com
UAT_SERVER_USER = deploy
UAT_SERVER_SSH_KEY = (paste private key)

PROD_SERVER_HOST = api.your-domain.com
PROD_SERVER_USER = deploy
PROD_SERVER_SSH_KEY = (paste private key)
```

### Slack Notifications
```
SLACK_WEBHOOK = https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_WEBHOOK_QA = https://hooks.slack.com/services/YOUR/QA/URL
SLACK_WEBHOOK_PROD = https://hooks.slack.com/services/YOUR/PROD/URL
SLACK_WEBHOOK_CRITICAL = https://hooks.slack.com/services/YOUR/CRITICAL/URL
```

### Database & Redis (Production)
```
PROD_DATABASE_URL = postgresql://user:pass@host:5432/dbname
PROD_REDIS_URL = redis://host:6379/0
```

---

## 📝 Bước 7: Setup Environments (cho Manual Approval)

Vào GitHub → Settings → Environments

### 1. Create "uat" environment:
- Click **"New environment"**
- Name: `uat`
- **Optional:** Add required reviewers (QA team)
- **Optional:** Wait timer: 0 minutes
- Click **"Configure environment"**

### 2. Create "production" environment:
- Name: `production`
- ✅ **Required reviewers:** Add 2+ people (Tech Lead, DevOps)
- ✅ **Wait timer:** 5 minutes (safety buffer)
- ✅ **Deployment branches:** Only protected branches
- Environment secrets: Add production-specific secrets
- Click **"Configure environment"**

---

## 🎯 Bước 8: First Push Complete

```bash
# Đảm bảo đang ở develop branch
git checkout develop

# Pull latest (trong trường hợp có changes từ GitHub)
git pull origin develop

# Push all branches
git push --all origin

# Push tags (nếu có)
git push --tags origin

# Verify trên GitHub
# - Check all branches tồn tại: main, develop, uat
# - Check Branch Protection rules active
# - Check GitHub Actions workflows visible
```

---

## ✅ Bước 9: Test CI/CD Workflow

### Test Develop Workflow:
```bash
# Tạo feature branch
git checkout develop
git checkout -b feature/test-ci

# Make a small change
echo "# Test CI" >> TEST.md
git add TEST.md
git commit -m "test: verify CI/CD pipeline"

# Push và tạo PR
git push origin feature/test-ci

# Vào GitHub:
# 1. Create Pull Request: feature/test-ci → develop
# 2. Xem CI/CD chạy trong "Checks" tab
# 3. Nếu pass, merge PR
# 4. Check develop branch CI/CD chạy và deploy to DEV
```

### Test Production Workflow:
```bash
# Tạo tag release
git checkout main
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Check GitHub Actions:
# 1. Production workflow được trigger
# 2. All tests chạy
# 3. Docker images được build
# 4. Chờ manual approval trong "production" environment
# 5. Click "Review deployments" → Approve
# 6. Deployment chạy
```

---

## 📊 Bước 10: Setup Monitoring & Alerts (Optional)

### Codecov (Code Coverage):
1. Đăng nhập https://codecov.io
2. Link GitHub account
3. Enable repository
4. Copy token
5. Add to GitHub Secrets: `CODECOV_TOKEN`

### Sentry (Error Tracking):
1. Tạo project trên https://sentry.io
2. Copy DSN
3. Add to GitHub Secrets: `SENTRY_DSN`
4. Update .env files với DSN

---

## 🔄 Daily Workflow

### Bắt đầu ngày:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/new-feature
# Code...
```

### Kết thúc task:
```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
# Create PR on GitHub
```

### Review PR:
```bash
# Pull request changes locally to test
git fetch origin
git checkout feature/someone-else-feature
# Test code
# Comment on PR
```

---

## 🚨 Emergency Hotfix

```bash
# From main branch
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# Fix bug
git add .
git commit -m "hotfix: fix critical trading calculation"

# Push và create PR to main
git push origin hotfix/critical-bug

# Sau khi merge vào main:
# Merge vào develop
git checkout develop
git merge main
git push origin develop

# Merge vào uat
git checkout uat
git merge main
git push origin uat
```

---

## 📚 Useful Git Commands

```bash
# Xem branch structure
git log --oneline --graph --all --decorate

# Xem changes
git diff
git diff --staged

# Undo commit (giữ changes)
git reset --soft HEAD~1

# Undo commit (xóa changes)
git reset --hard HEAD~1

# Stash changes
git stash
git stash pop

# Clean untracked files
git clean -fd

# View remote branches
git branch -r

# Delete local branch
git branch -d feature/old-feature

# Delete remote branch
git push origin --delete feature/old-feature

# Sync with remote
git fetch --prune
```

---

## ⚠️ Warnings & Best Practices

### ❌ KHÔNG BAO GIỜ:
- Commit file .env
- Commit passwords, API keys
- Force push to main/develop (`git push -f`)
- Commit directly to main (always use PR)
- Merge without review

### ✅ LUÔN LUÔN:
- Pull before push
- Test locally trước khi push
- Write meaningful commit messages
- Request code review
- Update documentation
- Add tests for new features

---

## 🎓 Git Commit Message Examples

```bash
# Features
git commit -m "feat: add stop-loss configuration to strategies"
git commit -m "feat(auth): implement 2FA authentication"

# Bug fixes
git commit -m "fix: correct balance calculation for margin accounts"
git commit -m "fix(websocket): handle reconnection on network failure"

# Documentation
git commit -m "docs: update API documentation for v1.1"
git commit -m "docs(readme): add installation instructions"

# Refactoring
git commit -m "refactor: extract order validation to separate service"
git commit -m "refactor(database): optimize query performance"

# Tests
git commit -m "test: add integration tests for backtest engine"
git commit -m "test(auth): increase coverage to 95%"

# Chores
git commit -m "chore: update dependencies to latest versions"
git commit -m "chore(ci): add code coverage reporting"
```

---

## 🎉 Congratulations!

Project của bạn đã được setup chuẩn professional trên GitHub với:
- ✅ Branch protection
- ✅ CI/CD pipelines
- ✅ Manual approval cho production
- ✅ Automated testing
- ✅ Code review process
- ✅ Documentation
- ✅ Monitoring & alerts

**Next Steps:**
1. Invite team members to repository
2. Setup Slack notifications
3. Configure production servers
4. Run first deployment to UAT
5. Celebrate! 🎊
