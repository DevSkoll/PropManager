# Contributing to PropManager

Thank you for your interest in contributing to PropManager! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [License](#license)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## License

PropManager is licensed under **AGPL-3.0**. By contributing, you agree that your contributions will be licensed under the same terms.

**Important**: If you are interested in using PropManager under different licensing terms (e.g., for proprietary use), please contact us about dual-licensing options.

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis (for Django-Q2 task queue)
- Node.js 18+ (optional, for frontend assets)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/propmanager.git
   cd propmanager
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

5. **Set up the database**
   ```bash
   python manage.py migrate
   python manage.py seed_dev_data  # Optional: load test data
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

For detailed setup instructions, see [docs/development/getting-started.md](docs/development/getting-started.md).

## Development Workflow

### Branch Naming

Use descriptive branch names with prefixes:

- `feature/` - New features (e.g., `feature/tenant-rewards`)
- `fix/` - Bug fixes (e.g., `fix/invoice-calculation`)
- `docs/` - Documentation updates (e.g., `docs/api-reference`)
- `refactor/` - Code refactoring (e.g., `refactor/payment-gateway`)
- `test/` - Test additions or fixes (e.g., `test/billing-edge-cases`)

### Commit Messages

Write clear, concise commit messages:

```
<type>: <short description>

<optional longer description>

<optional footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting (no code change)
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

**Examples:**
```
feat: Add automated late fee calculation

Implements PropertyBillingConfig-based late fee calculation
that runs daily via Django-Q2 task.

Closes #123
```

```
fix: Correct invoice due date for month-to-month leases
```

### Making Changes

1. Create a feature branch from `master`
   ```bash
   git checkout -b feature/your-feature
   ```

2. Make your changes with clear, focused commits

3. Write or update tests as needed

4. Ensure all tests pass
   ```bash
   python manage.py test
   ```

5. Run code quality checks
   ```bash
   black .
   isort .
   flake8
   ```

6. Push your branch and create a pull request

## Coding Standards

### Python Style

- Follow **PEP 8** guidelines
- Use **Black** for code formatting (line length: 88)
- Use **isort** for import sorting
- Maximum line length: 88 characters

### Code Organization

- **Models**: Define in `models.py` with clear docstrings
- **Views**: Use class-based views where appropriate
- **URLs**: Keep URL patterns clean and RESTful
- **Templates**: Use template inheritance, avoid duplication
- **Forms**: Validate thoroughly, provide clear error messages

### Django Best Practices

- Use `TimeStampedModel` for audit fields (`created_at`, `updated_at`)
- Use `AuditMixin` for user tracking (`created_by`, `updated_by`)
- Prefer model managers for complex queries
- Use signals sparingly; prefer explicit method calls
- Keep views thin; put business logic in models or services

### Security

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user input
- Use Django's built-in CSRF protection
- Follow OWASP security guidelines

## Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.billing

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Writing Tests

- Place tests in `tests/` directory within each app
- Use descriptive test method names
- Test edge cases and error conditions
- Mock external services (payment gateways, APIs)

**Example:**
```python
class InvoiceModelTest(TestCase):
    def test_calculate_total_with_late_fee(self):
        """Invoice total should include late fee when past due date."""
        invoice = InvoiceFactory(
            amount=Decimal("1000.00"),
            due_date=date.today() - timedelta(days=5)
        )
        invoice.apply_late_fee()
        self.assertEqual(invoice.total, Decimal("1050.00"))
```

## Pull Request Process

### Before Submitting

1. Ensure your code follows the coding standards
2. Write or update tests for your changes
3. Update documentation if needed
4. Run the full test suite
5. Rebase on latest `master` if needed

### PR Requirements

- Clear title describing the change
- Description explaining what and why
- Reference related issues
- All tests passing
- Code review approval

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
How was this tested?

## Related Issues
Closes #XXX

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guidelines
```

### Review Process

1. Submit PR against `master` branch
2. Request review from maintainers
3. Address feedback and update as needed
4. Squash commits if requested
5. Maintainer merges when approved

## Reporting Issues

### Bug Reports

Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Screenshots if applicable

### Feature Requests

Include:
- Clear description of the feature
- Use case / problem it solves
- Proposed implementation (optional)
- Willingness to contribute

### Security Issues

**Do not report security vulnerabilities publicly.**

See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

## Questions?

- Open a GitHub Discussion for general questions
- Check existing issues before creating new ones
- Review documentation in the `docs/` directory

---

Thank you for contributing to PropManager!
