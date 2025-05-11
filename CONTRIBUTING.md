# 🤝 Contributing

Thank you for your interest in contributing to **RME Toolkit**!
This guide will walk you through setting up your environment, maintaining code quality, testing, and submitting changes.

## 1. Set Up Your Development Environment

Install dependencies using [**uv**](https://github.com/astral-sh/uv), our package and virtual environment manager.

<details>
<summary><strong>Show setup instructions</strong></summary>

```bash
# Clone the repository
git clone https://github.com/reverseame/rme-toolkit.git
cd rme-toolkit
```

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate    # On Windows: .\venv\Scripts\activate
```

```bash
# Install dependencies from the global pyproject.toml
# Create and activate virtual environment
uv pip install -r requirements.txt
```

> [!NOTE] If you don't have a `requirements.txt` yet, you can generate it from your `pyproject.toml` using:
>
> ```bash
> uv pip compile pyproject.toml > requirements.txt
> ```

```bash
# Install pre-commit hooks
pre-commit install
```

> [!NOTE]
> if `uv` is not installed, you can install it with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

</details>

## 2. Create a Feature or Fix Branch

Work on a dedicated branch for your changes, following naming conventions.

<details> <summary><strong>Show branch naming guide</strong></summary>

```bash
# Use one of the following formats
git checkout -b feat/your-feature-name
git checkout -b fix/short-bug-description
```

</details>

## 3. Format and Lint Your Code

We use `ruff` to ensure code quality and consistency.

<details> <summary><strong>Show lint & format commands</strong></summary>

```bash
# Check for lint issues
ruff check .
```

```bash
# Auto-format the code
ruff format .
```

```bash
# (Optional) Run pre-commit hooks manually
pre-commit run --all-files
```

</details>

## 4. Run Tests

We use `pytest` with `pytest-cov`.
Since the code is in a `src/` layout, you must set `PYTHONPATH=src`.

<details> <summary><strong>Show test commands</strong></summary>

```bash
# Run the full test suite with coverage
PYTHONPATH=src pytest --cov=src tests
```

```bash
# Or test a specific package
PYTHONPATH=src pytest packages/my_package/tests
```

</details>

## 5. Use Conventional Commits

All commit messages must follow the conventional commit format via Commitizen.

<details> <summary><strong>Show commit and changelog commands</strong></summary>

```bash
# Create a commit with Commitizen
cz commit
```

```bash
# (Optional) Bump version and generate changelog
cz bump --changelog
```

</details>

## 6. Add a New Package

All packages live under `packages/` and use the root environment.

<details> <summary><strong>Show package creation steps</strong></summary>

```bash
# Create a new package folder
mkdir -p packages/my_package
```

```bash
# (Optional) Add tests folder
mkdir -p packages/my_package/tests
```

```bash
# Initialize pyproject.toml using uv
cd packages
uv init --package my_new_package
```

```bash
# Run it
uv run my-new-package
```

</details>

## Before Submitting

Make sure your code meets the following checklist:

<details> <summary><strong>PR checklist</strong></summary>

- Code is linted (`ruff check .`) and formatted (`ruff format .`)
- All tests pass (`PYTHONPATH=src pytest`)
- Commits follow conventional commit standards (`cz commit`)
- Version bumped and changelog updated (if needed)
- PR targets the `dev` branch

</details>
