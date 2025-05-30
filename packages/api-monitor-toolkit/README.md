# 🐍 API Monitor Toolkit

A command-line tool to extract and analyze API Monitor data from running Windows processes. It supports detailed capture of parameters and call stacks, with flexible output options including streaming JSON to stdout, file, or HTTP endpoints. Perfect for automating API monitoring workflows and integrating with other tools.

## 📦 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/reverseame/rme-Python-toolkit.git
cd rme-Python-toolkit/packages/api-monitor-toolkit
```

### 2. Set Up the Environments

Use the provided `Makefile` to create and install both 32-bit and 64-bit environments:

> [!IMPORTANT]
> Make sure you have Python 3.13 32-bit and 64-bit installed, and their paths are correctly set in the Makefile.

```bash
make install32    # Create and install the 32-bit virtual environment
make install64    # Create and install the 64-bit virtual environment
```

<details> <summary><strong>⚠️ Why both?</strong></summary>

This toolkit reads memory directly from Windows applications (e.g., API Monitor) using low-level system APIs.
Because of Windows architecture restrictions, you must use a Python interpreter with the same bitness (32 or 64) as the target application:
- If the target process is 32-bit → you must run the scraper with Python 32-bit.
- If the target process is 64-bit → you must run the scraper with Python 64-bit.
That's why this project uses two separate virtual environments: one for each architecture.
</details>

### 3. Run the Tool

Use the appropriate environment depending on the architecture of the target application:

▶️ 64-bit Mode:

```bash
make run64 ARGS="spider -p -c -o output.json -v"
```

▶️ 32-bit Mode:

```bash
make run32 ARGS="spider -p -c -o output.json -v"
```

## ✨ Features

- Extracts detailed API call information from API Monitor.
- Supports selective retrieval of Parameters and Call Stack sections.
- Multiple output modes: streaming JSON to stdout, save as file, or HTTP POST.
- Automatic detection of target process architecture (32/64-bit).
- Verbose logging with incremental output to handle large datasets efficiently.

## 🚀 Usage Example

```bash
uv run api-monitor-toolkit spider --parameters --call-stack -o output.json -v
```

## 📂 Output

The tool outputs structured JSON data including:

```json
[
    {
        "id": 1,
        "timestamp": "5/29/2025 6:54:28 PM",
        "time": "6:54:28.018 PM",
        "rel_time": "0:00:00:015",
        "thread": 1,
        "tid": 6864,
        "module": "beep_g++_O0_windows_x64.exe",
        "category": "Critical Section",
        "api": "InitializeCriticalSection ( 0x00007ff787e27100 )",
        "return_type": "void",
        "return_value": "undefined",
        "return_address": "0x00007ff787e21d18",
        "error": "undefined",
        "duration": 1e-07,
        "full_category": "System Services / Synchronization / Critical Section",
        "parameters": [
            {
            "id": 1,
            "type": "LPCRITICAL_SECTION",
            "name": "lpCriticalSection",
            "before": "0x00007ff787e27100 = { DebugInfo = NULL, LockCount = 0, RecursionCount = 0  ...}",
            "after": "0x00007ff787e27100 = { DebugInfo = 0xffffffffffffffff, LockCount = -1, RecursionCount = 0  ...}"
            }
        ],
        "call_stack": [
            {
                "id": 1,
                "module": "beep_g++_O0_windows_x64.exe",
                "address": "0x00007ff787e21d18",
                "offset": "0x1d18",
                "location": "undefined"
            },...
        ]
    }
]
```
