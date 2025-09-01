# 🐍 API Monitor Toolkit

A command-line tool to extract and analyze API Monitor data from running Windows processes. It supports detailed capture of parameters and call stacks, with flexible output options including streaming JSON to stdout, file, or HTTP endpoints. Perfect for automating API monitoring workflows and integrating with other tools.

## 📦 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/reverseame/rme-Python-toolkit.git
cd rme-Python-toolkit/packages/api-monitor-toolkit
```

### 2. Prepare the Environment

This tool uses uv for environment management. You need to run it with a Python interpreter that matches the bitness (32-bit or 64-bit) of the target process you want to monitor.

> [!IMPORTANT]
> Ensure that you have the correct version of Python installed (32-bit or 64-bit), depending on the architecture of the target process.

### 3. Run the Tool

You can run the tool with a specific Python interpreter using the `--python` flag. Example:

```bash
uv run --python "$env:PYTHON64" -- api-monitor-toolkit analyzer -i <path_to_exe> -v
```

```bash
$env:PYTHON64 = "..."
uv run --python "$env:PYTHON64" -- api-monitor-toolkit spider -i <path_to_apmx> -p -c -o output.json -v
```

If you have more than one `.apmx` file to extract, you can use this one-liner in PowerShell to automate the extraction:

```powershell
Get-ChildItem .\samples -Filter *.apmx64 | ForEach-Object { uv run --python "$env:PYTHON64" -- api-monitor-toolkit spider -i $_.FullName -p -r "C:\\rohitab.com\\API Monitor\\" -c -o "$($_.BaseName).json" -v }
```

> [!TIP]
> you can use `uv python list` to list your environments

Replace `<path_to_python>` with the path to your Python **32-bit** or **64-bit** interpreter.

<details> 
<summary>
<strong>⚠️ Why bitness matters?</strong>
</summary>

This toolkit reads memory directly from API Monitor using low-level system APIs.
Because of Windows architecture restrictions, you must use a Python interpreter with the same bitness (32 or 64) as the target application:
- If the target process is 32-bit → you must run the scraper with Python 32-bit.
- If the target process is 64-bit → you must run the scraper with Python 64-bit.

</details>

## ✨ Features

- Extracts detailed API call information from API Monitor.
- Supports selective retrieval of Parameters and Call Stack sections.
- Multiple output modes: streaming JSON to stdout, save as file, or HTTP POST.
- Verbose logging with incremental output to handle large datasets efficiently.

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
            },...
        ],
        "call_stack": [
            {
                "id": 1,
                "module": "beep_g++_O0_windows_x64.exe",
                "address": "0x00007ff787e21d18",
                "offset": "0x1d18",
                "location": "undefined"
            },...
        ],
        "metadata": {
            "path": "C:\\Users\\htoral\\Desktop\\beep_g++_O0_windows_x64.exe", 
            "filename": "beep_g++_O0_windows_x64.exe", 
            "pid": 4444
        }
    }
]
```
