# Production Deployment Guide

## 🌍 Môi Trường (Environments)

### 1. **Development (DEV)**
- **Branch:** `develop`
- **Purpose:** Môi trường phát triển cho developers
- **Database:** PostgreSQL Dev instance
- **Domain:** `dev.trading-bot.com` (hoặc localhost)
- **Auto Deploy:** Mọi commit vào `develop` branch

### 2. **User Acceptance Testing (UAT/Staging)**
- **Branch:** `uat` hoặc `staging`
- **Purpose:** Testing bởi QA team và stakeholders trước khi production
- **Database:** PostgreSQL UAT instance (data giống PROD nhưng anonymized)
- **Domain:** `uat.trading-bot.com` hoặc `staging.trading-bot.com`
- **Deploy:** Manual approval sau khi merge PR vào UAT branch

### 3. **Production (PROD)**
- **Branch:** `main` hoặc `master`
- **Purpose:** Môi trường thật phục vụ end users
- **Database:** PostgreSQL Production với backup tự động
- **Domain:** `trading-bot.com` hoặc `api.trading-bot.com`
- **Deploy:** Manual approval + tagged release only

---

## 🌲 Git Branching Strategy (GitFlow)

```
main (production)
  │
  ├─── uat/staging (pre-production testing)
  │      │
  │      └─── develop (integration)
  │             │
  │             ├─── feature/user-authentication
  │             ├─── feature/backtest-optimization
  │             ├─── bugfix/websocket-reconnect
  │             └─── hotfix/critical-order-bug (merge trực tiếp vào main)
```

### Branch Naming Convention

- **feature/**: Tính năng mới
  - `feature/add-risk-alerts`
  - `feature/multi-exchange-support`

- **bugfix/**: Fix bug trong develop/uat
  - `bugfix/fix-login-timeout`
  - `bugfix/incorrect-balance-calculation`

- **hotfix/**: Fix bug khẩn cấp trong production
  - `hotfix/critical-order-execution`
  - `hotfix/security-vulnerability`

- **release/**: Chuẩn bị release version
  - `release/v1.2.0`
  - `release/v2.0.0-beta`

---

## 🔄 Quy Trình Làm Việc (Workflow)

### Tính Năng Mới (New Feature)

```bash
# 1. Tạo branch từ develop
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# 2. Code và commit
git add .
git commit -m "feat: add risk alert system"

# 3. Push và tạo Pull Request
git push origin feature/your-feature-name
# Tạo PR: feature/your-feature-name → develop
```

### Review Process

1. **Code Review:** Ít nhất 1-2 người review
2. **CI/CD Checks:** All tests must pass
3. **Merge:** Squash and merge hoặc Merge commit
4. **Delete Branch:** Xóa feature branch sau khi merge

### Đưa Lên UAT

```bash
# 1. Merge develop → uat
git checkout uat
git pull origin uat
git merge develop
git push origin uat

# 2. Auto deploy hoặc manual trigger CI/CD
# 3. QA team test trên UAT environment
```

### Đưa Lên Production

```bash
# 1. Tạo release branch
git checkout develop
git checkout -b release/v1.2.0

# 2. Update version numbers, CHANGELOG
# Edit pyproject.toml, package.json
git add .
git commit -m "chore: bump version to 1.2.0"

# 3. Merge vào main
git checkout main
git merge release/v1.2.0
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin main --tags

# 4. Merge lại vào develop
git checkout develop
git merge release/v1.2.0
git push origin develop

# 5. Deploy production (manual approval)
```

---

## 🚨 Hotfix (Khẩn Cấp)

```bash
# 1. Tạo hotfix từ main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 2. Fix bug và commit
git add .
git commit -m "hotfix: fix critical order execution bug"

# 3. Merge vào main
git checkout main
git merge hotfix/critical-bug
git tag -a v1.2.1 -m "Hotfix: Critical bug"
git push origin main --tags

# 4. Merge vào develop và uat
git checkout develop
git merge hotfix/critical-bug
git push origin develop

git checkout uat
git merge hotfix/critical-bug
git push origin uat

# 5. Deploy immediately
```

---

## 🔒 Branch Protection Rules (GitHub Settings)

### Main Branch Protection
```yaml
- Require pull request reviews (2 reviewers)
- Require status checks to pass:
  - CI/CD tests
  - Security scan
  - Code coverage > 80%
- Require branches to be up to date
- Include administrators: No
- Restrict who can push: Only CI/CD service
```

### UAT Branch Protection
```yaml
- Require pull request reviews (1 reviewer)
- Require status checks to pass
- Allow force push: No
```

### Develop Branch Protection
```yaml
- Require status checks to pass
- Allow force push: No
```

---

## 📋 Pull Request Template

Create `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## 📝 Description
<!-- Mô tả tính năng hoặc bug fix -->

## 🔗 Related Issues
<!-- Link đến issue: Closes #123 -->

## 🧪 Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Tested locally
- [ ] Tested on dev environment

## 📸 Screenshots (if UI changes)
<!-- Add screenshots here -->

## ✅ Checklist
- [ ] Code follows project style guide
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Database migrations included (if needed)
- [ ] Environment variables documented
```

---

## 🤖 CI/CD Pipeline (GitHub Actions)

### Workflow Tự Động

**On Push to Develop:**
1. Run linters (black, isort, eslint)
2. Run tests (pytest, jest)
3. Build Docker images
4. Deploy to DEV environment
5. Run smoke tests

**On Push to UAT:**
1. Same as develop
2. Deploy to UAT environment
3. Run E2E tests
4. Send Slack notification to QA team

**On Push to Main (Tagged Release):**
1. Run full test suite
2. Build production Docker images
3. **Manual approval required**
4. Deploy to PROD
5. Run health checks
6. Send success notification

---

## 🏷️ Semantic Versioning

Follow **SemVer**: `MAJOR.MINOR.PATCH`

- **MAJOR (1.x.x):** Breaking changes
- **MINOR (x.1.x):** New features (backward compatible)
- **PATCH (x.x.1):** Bug fixes

Example:
- `v1.0.0` → Initial production release
- `v1.1.0` → Added backtesting feature
- `v1.1.1` → Fixed WebSocket reconnection bug
- `v2.0.0` → API redesign (breaking changes)

---

## 📦 Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Database migrations tested
- [ ] Environment variables documented
- [ ] Rollback plan prepared
- [ ] Stakeholders notified
- [ ] Performance benchmarks checked
- [ ] Security scan completed
- [ ] Backup verified

---

## 🔐 Environment Variables Management

**DO NOT commit:**
- `.env` files
- API keys
- Database passwords
- JWT secrets

**Use:**
- GitHub Secrets for CI/CD
- AWS Secrets Manager / Vault for production
- `.env.example` for documentation

---

## 📊 Monitoring & Alerts

**After Deployment:**
- Check application logs
- Monitor error rates (Sentry)
- Check database performance
- Monitor API response times
- Verify WebSocket connections
- Check Redis cache hit rate

**Rollback Triggers:**
- Error rate > 5%
- Response time > 2s
- Critical functionality broken
- Database migration failed

---

## 🎯 Best Practices

1. **Small, Frequent Commits**: Better than large commits
2. **Meaningful Commit Messages**: Follow Conventional Commits
3. **Test Before Push**: Run tests locally first
4. **Keep Branches Up-to-Date**: Regularly merge develop
5. **Delete Merged Branches**: Keep repo clean
6. **Document Everything**: README, API docs, deployment notes
7. **Security First**: Never expose secrets
8. **Monitor Production**: Set up alerts and logging

---

## 📝 Commit Message Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Build/tooling changes

**Examples:**
```
feat(backtest): add stop-loss configuration
fix(websocket): reconnect on connection drop
docs(api): update authentication endpoints
chore(deps): upgrade FastAPI to 0.115.0
```

---

## 🚀 Quick Start for Team

```bash
# 1. Clone repository
git clone git@github.com:your-org/trading-bot-platform.git
cd trading-bot-platform

# 2. Setup develop branch
git checkout develop

# 3. Create your feature branch
git checkout -b feature/your-name-feature

# 4. Setup development environment
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install

# 5. Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 6. Start coding!
```

---

## 📚 Additional Resources

- [GitFlow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
