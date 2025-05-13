# 🛡️ IOC Extractor

This Python script is a specialized tool for extracting Indicators of Compromise (IOCs) from JSON logs extracted from [API Monitor](http://www.rohitab.com/apimonitor). It uses a customizable pattern-matching system defined in a separate JSON rules file to identify relevant entries and extract key fields, even from complex or nested data structures.

Designed with performance and flexibility in mind, it supports streaming large log files efficiently and includes optional performance monitoring for profiling or optimization purposes.

## 📦 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/reverseame/rme-toolkit.git
cd rme-toolkit/packages/ioc-extractor
```

### 2. Install Dependencies

```bash
uv venv                             # Create a virtual environment
source .venv/bin/activate           # Activate it (use .venv\Scripts\activate on Windows)
```

```bash
uv pip compile pyproject.toml > requirements.txt
uv pip install -r requirements.txt
```

### 3. Run the Tool

```bash
uv run ioc-extractor --input <input_file.json> --patterns <patterns_file.yaml> [-v]
```

## ✨ Features

- **Pattern-based IOC detection**: Use flexible rules (regex, exact match, substring) to define what constitutes a match.
- **Designed for API Monitor output**: Compatible with the JSON structure used by API Monitor's export feature.
- **Nested and list-aware field extraction**: Select fields deeply nested inside the JSON or embedded in key-value arrays.
- **Text transformation support**: Apply modifiers like regex extraction, case conversion, and quote stripping.
- **Efficient for large logs**: Uses stream parsing (`ijson`) to process huge files with minimal memory usage.
- **Optional performance metrics**: Track CPU and memory usage in real time using `psutil`.

## 🚀 Usage Example

```bash
uv run ioc-extractor --input <input_file.json> --patterns <patterns_file.json> [-v]
```
