# Development Workflow

This guide covers the development workflow for contributing to PropManager, including Git practices, code review, and deployment.

## Table of Contents

- [Git Workflow](#git-workflow)
- [Branch Strategy](#branch-strategy)
- [Making Changes](#making-changes)
- [Commit Guidelines](#commit-guidelines)
- [Pull Requests](#pull-requests)
- [Code Review](#code-review)
- [Continuous Integration](#continuous-integration)
- [Deployment](#deployment)

---

## Git Workflow

PropManager uses a simplified Git workflow based on feature branches.

### Overview

```
master (production-ready)
  │
  ├── feature/new-feature
  │     └── commits...
  │
  ├── fix/bug-fix
  │     └── commits...
  │
  └── docs/update-readme
        └── commits...
```

### Key Principles

1. **master is always deployable** - Never push broken code to master
2. **Feature branches are short-lived** - Merge frequently to avoid conflicts
3. **Pull requests are required** - No direct commits to master
4. **Tests must pass** - All PRs require passing CI checks

---

## Branch Strategy

### Branch Naming Convention

Use descriptive prefixes:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New functionality | `feature/tenant-rewards` |
| `fix/` | Bug fixes | `fix/invoice-calculation` |
| `docs/` | Documentation | `docs/api-reference` |
| `refactor/` | Code restructuring | `refactor/payment-service` |
| `test/` | Test additions | `test/billing-edge-cases` |
| `chore/` | Maintenance | `chore/update-dependencies` |

### Branch Name Guidelines

- Use lowercase letters
- Separate words with hyphens
- Keep names concise but descriptive
- Include ticket number if applicable: `feature/PM-123-tenant-rewards`

### Creating a Branch

```bash
# Update master
git checkout master
git pull origin master

# Create feature branch
git checkout -b feature/your-feature-name
```

---

## Making Changes

### Development Cycle

1. **Create branch** from latest master
2. **Write code** with small, focused commits
3. **Test locally** - run tests and manual verification
4. **Create PR** when ready for review
5. **Address feedback** from code review
6. **Merge** after approval

### Local Testing

Before creating a PR:

```bash
# Run all tests
python manage.py test

# Run linting
flake8

# Format code
black .
isort .

# Check for common issues
python manage.py check
```

### Keeping Branch Updated

If master has changed while you're working:

```bash
# Option 1: Rebase (preferred for clean history)
git fetch origin
git rebase origin/master

# Option 2: Merge (if conflicts are complex)
git fetch origin
git merge origin/master
```

---

## Commit Guidelines

### Commit Message Format

```
<type>: <short description>

<optional body>

<optional footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |
| `perf` | Performance improvements |

### Writing Good Commit Messages

**Good examples:**
```
feat: Add streak-based tenant rewards

Implements reward calculation for consecutive on-time payments.
Rewards are granted at 3, 6, and 12-month milestones.

Closes #45
```

```
fix: Correct late fee calculation for partial payments

Late fees were being applied to full invoice amount instead of
remaining balance. Now correctly calculates based on unpaid amount.
```

```
refactor: Extract payment processing into service class

Moves payment logic from views to dedicated PaymentService class
for better testability and reuse.
```

**Bad examples:**
```
# Too vague
fix: Fixed bug

# No context
update stuff

# Multiple changes in one commit
Add rewards, fix billing, update docs
```

### Atomic Commits

Each commit should:
- Represent one logical change
- Be independently reversible
- Pass all tests
- Have a clear purpose

**Split large changes:**
```bash
# Instead of one large commit, make several:
git add apps/billing/models.py
git commit -m "feat: Add PropertyBillingConfig model"

git add apps/billing/tasks.py
git commit -m "feat: Add late fee calculation task"

git add apps/billing/tests/
git commit -m "test: Add late fee calculation tests"
```

---

## Pull Requests

### Creating a Pull Request

1. Push your branch:
   ```bash
   git push -u origin feature/your-feature
   ```

2. Open PR on GitHub

3. Fill in the template:

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring
- [ ] Other (describe)

## How Has This Been Tested?
Describe the tests you ran.

## Related Issues
Closes #123

## Checklist
- [ ] My code follows the project style guidelines
- [ ] I have added tests for my changes
- [ ] All new and existing tests pass
- [ ] I have updated documentation as needed
- [ ] My changes don't introduce security vulnerabilities
```

### PR Best Practices

1. **Keep PRs focused** - One feature or fix per PR
2. **Write clear descriptions** - Explain what and why
3. **Include screenshots** - For UI changes
4. **Link related issues** - Use "Closes #123" syntax
5. **Request specific reviewers** - Tag relevant team members

### PR Size Guidelines

| Size | Lines Changed | Review Time |
|------|---------------|-------------|
| Small | < 100 | Quick review |
| Medium | 100-300 | Standard review |
| Large | 300-500 | Split if possible |
| Very Large | > 500 | Should be split |

Large PRs are harder to review and more likely to have issues. Split into smaller, logical PRs when possible.

---

## Code Review

### As a Reviewer

1. **Check functionality** - Does the code work as intended?
2. **Review tests** - Are changes properly tested?
3. **Check style** - Does it follow project conventions?
4. **Security review** - Any potential vulnerabilities?
5. **Performance** - Any obvious performance issues?

### Review Comments

**Be constructive:**
```
# Good
Consider using select_related() here to avoid N+1 queries.
This pattern is used elsewhere in apps/leases/views.py:45.

# Bad
This is wrong.
```

**Ask questions:**
```
# Good
I'm not sure I understand the use case for this.
Could you explain when this condition would be true?

# Bad
What is this?
```

### Review Checklist

- [ ] Code compiles and tests pass
- [ ] Logic is correct and handles edge cases
- [ ] Error handling is appropriate
- [ ] No security vulnerabilities introduced
- [ ] Code follows project style
- [ ] Tests cover new functionality
- [ ] Documentation is updated

### As an Author

1. **Respond to all comments** - Don't leave things unresolved
2. **Explain your decisions** - Provide context when asked
3. **Make requested changes** - Or discuss alternatives
4. **Re-request review** - After making changes
5. **Be open to feedback** - Code review improves everyone

---

## Continuous Integration

### CI Pipeline

PropManager uses GitHub Actions for CI:

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python manage.py test
      - run: flake8
```

### CI Checks

All PRs must pass:

| Check | Description |
|-------|-------------|
| Tests | All tests pass |
| Linting | No flake8 errors |
| Formatting | Black formatting check |
| Migrations | No missing migrations |

### Running CI Locally

Before pushing, run the same checks locally:

```bash
# Full CI check
python manage.py test
flake8
black --check .
python manage.py makemigrations --check --dry-run
```

---

## Deployment

### Deployment Workflow

```
feature branch → PR → code review → merge to master → deploy
```

### Pre-Deployment Checklist

- [ ] All tests pass
- [ ] Migrations are included
- [ ] Environment variables documented
- [ ] Deployment notes in PR
- [ ] Rollback plan considered

### Deployment Steps

1. **Merge PR** to master
2. **Deploy** using your deployment method
3. **Run migrations** in production
4. **Verify** functionality
5. **Monitor** for errors

### Post-Deployment

1. Check application logs
2. Verify critical functionality
3. Monitor error tracking
4. Test user-facing features

### Rollback

If issues are found:

```bash
# Revert the merge commit
git revert <merge-commit-sha>
git push origin master

# Redeploy previous version
# Roll back migrations if necessary
python manage.py migrate app_name <previous_migration>
```

---

## Tips for Success

### Daily Workflow

1. Pull latest changes each morning
2. Work in small increments
3. Commit frequently
4. Push at end of day (for backup)

### Avoiding Merge Conflicts

1. Keep branches short-lived
2. Communicate with team
3. Rebase frequently
4. Split large changes

### Getting Reviews Faster

1. Keep PRs small
2. Write clear descriptions
3. Tag appropriate reviewers
4. Respond quickly to feedback

---

## Further Reading

- [Getting Started](getting-started.md) - Development setup
- [Background Tasks](tasks.md) - Django-Q2 guide
- [Contributing](../../CONTRIBUTING.md) - Contribution guidelines
