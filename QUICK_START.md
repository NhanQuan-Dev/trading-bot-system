# Quick Start Guide

## 🚀 For New Team Members

### 1. Prerequisites
- Git installed
- Docker & Docker Compose (recommended)
- OR: Python 3.12+, PostgreSQL 16, Redis 7, Node.js 20+

### 2. Clone Repository
```bash
git clone git@github.com:your-org/trading-bot-platform.git
cd trading-bot-platform
```

### 3. Setup Development Branch
```bash
git checkout develop
git pull origin develop
```

### 4. Quick Start with Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Access:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Frontend: http://localhost:3000
```

### 5. Manual Setup (Without Docker)

#### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Start server
./run.sh
# OR: uvicorn src.main:app --reload
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Setup environment
cp .env.example .env

# Start dev server
npm run dev
```

### 6. Verify Setup
```bash
# Check backend health
curl http://localhost:8000/health

# Check database connection
curl http://localhost:8000/api/v1/exchanges

# Run tests
cd backend
pytest tests/integration/ -v
```

---

## 🌿 Working on a Feature

### 1. Create Feature Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### 2. Make Changes
```bash
# Code your feature
# Run tests frequently
pytest tests/ -v

# Commit with meaningful messages
git add .
git commit -m "feat: add stop-loss configuration"
```

### 3. Push and Create PR
```bash
git push origin feature/your-feature-name

# Go to GitHub and create Pull Request
# - Base: develop
# - Compare: feature/your-feature-name
# - Fill in PR template
# - Request reviewers
```

### 4. Address Review Comments
```bash
# Make changes based on feedback
git add .
git commit -m "fix: address review comments"
git push origin feature/your-feature-name
```

### 5. After Merge
```bash
# Switch back to develop
git checkout develop
git pull origin develop

# Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

---

## 🧪 Running Tests

### Backend
```bash
cd backend

# All tests
pytest tests/ -v

# Specific category
pytest tests/unit/ -v
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Single test file
pytest tests/integration/core/test_auth_api.py -v
```

### Frontend
```bash
cd frontend

# Lint
npm run lint

# Type check
npm run type-check

# Build
npm run build
```

---

## 🐛 Fixing a Bug

### Regular Bug (in develop)
```bash
git checkout develop
git pull origin develop
git checkout -b bugfix/fix-description

# Fix bug
# Add test to prevent regression
# Commit and push
# Create PR to develop
```

### Critical Bug (in production)
```bash
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-description

# Fix bug urgently
# Test thoroughly
# Create PR to main
# After merge, also merge to develop and uat
```

---

## 📚 Common Commands

### Git
```bash
# Update your branch with latest develop
git checkout develop
git pull origin develop
git checkout your-branch
git merge develop

# Resolve conflicts
git status
# Fix conflicts in files
git add .
git commit -m "merge: resolve conflicts with develop"

# Squash commits (before merging)
git rebase -i HEAD~3  # Squash last 3 commits
```

### Database
```bash
# Create migration
alembic revision -m "add new column"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current
```

### Docker
```bash
# Rebuild after code changes
docker-compose up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all
docker-compose down

# Clean up
docker-compose down -v  # Remove volumes
docker system prune -a  # Clean all
```

---

## 🔒 Security Reminders

- ⚠️ **Never commit .env files**
- ⚠️ **Never commit API keys or passwords**
- ⚠️ **Always use .env.example for documentation**
- ⚠️ **Rotate secrets regularly in production**

---

## 📞 Getting Help

- **Documentation**: Check `/docs` folder
- **API Docs**: http://localhost:8000/docs
- **Slack**: #trading-bot-dev channel
- **Issues**: Create GitHub issue with detailed description
- **Code Review**: Ask in PR comments

---

## ✅ Pre-Commit Checklist

Before pushing code:
- [ ] Code follows project style (black, isort)
- [ ] All tests pass locally
- [ ] No console.log or debug code
- [ ] Comments added for complex logic
- [ ] Documentation updated if needed
- [ ] .env.example updated if new variables added
- [ ] Commit messages are clear and descriptive

---

## 🎯 Key Files to Know

- `backend/src/main.py` - FastAPI application entry point
- `backend/src/trading/domain/` - Business logic
- `backend/src/trading/infrastructure/` - External services
- `backend/tests/conftest.py` - Test fixtures
- `frontend/src/pages/` - Page components
- `DEPLOYMENT_GUIDE.md` - Production deployment process
- `CHANGELOG.md` - Version history

---

## 💡 Pro Tips

1. **Use git aliases** for common commands
2. **Run tests before pushing** to catch issues early
3. **Keep PRs small** - easier to review
4. **Write descriptive commit messages** - helps future you
5. **Ask questions** - better to clarify than assume
6. **Review others' PRs** - learn and share knowledge
