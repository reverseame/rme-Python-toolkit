# 🧰 RME toolkit

A modular Python monorepo for building and maintaining RME tools with standardized development workflows and scalable package architecture.

## 📂 Repository Structure

```
├── packages/
│   └── package_a/      # Individual Python package/module
│       ├── src/
│       └── tests/
├── pyproject.toml      # Root-level configuration (linting, formatting, versioning)
├── requirements.txt    # Development and runtime dependencies
├── README.md           # Project overview
└── CONTRIBUTING.md     # Development and contribution guidelines
```

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/reverseame/rme-toolkit.git
cd rme-toolkit
```

### 2. Install dependencies

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate       # On Windows: .\venv\Scripts\activate
```

```bash
# Install dependencies
uv pip install -r pyproject.toml
```

```bash
# Set up pre-commit hooks
pre-commit install
```

### 3. Run the tool

```bash
# Example: run a module from a package
python packages/package_a/main.py
```

## 🤝 Contributing

We welcome contributions! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) guide for instructions on development workflow, coding standards, and submitting changes.

## 👥 Contributors

Thanks to all the people who contribute to this project!
[![Contributors](https://contrib.rocks/image?repo=reverseame/rme-toolkit)](https://github.com/reverseame/rme-toolkit/graphs/contributors)
