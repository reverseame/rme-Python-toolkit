# Replace with the actual Python executables on your machine if needed

# Common install paths (adjust if needed)
PYTHON32 = C:/Users/$(USERNAME)/AppData/Local/Programs/Python/Python313-32/python.exe
PYTHON64 = C:/Users/$(USERNAME)/AppData/Local/Programs/Python/Python313/python.exe

# CLI entry point
CLI = api-monitor-toolkit

.PHONY: all venv32 venv64 install32 install64 run32 run64 clean

# Install both environments
all: install32 install64

# Create 32-bit virtual environment
venv32:
	@echo "🔧 Creating 32-bit environment (.venv32)..."
	uv venv .venv32 --python $(PYTHON32) --seed

# Create 64-bit virtual environment
venv64:
	@echo "🔧 Creating 64-bit environment (.venv64)..."
	uv venv .venv64 --python $(PYTHON64) --seed

# Install the project in 32-bit venv
install32: venv32
	@echo "📦 Installing into .venv32..."
	uv pip install --python .venv32/Scripts/python.exe .

# Install the project in 64-bit venv
install64: venv64
	@echo "📦 Installing into .venv64..."
	uv pip install --python .venv64/Scripts/python.exe .

# Run CLI using 32-bit venv
run32:
	@echo "🚀 Running CLI using .venv32..."
	.venv32/Scripts/$(CLI) $(ARGS)

# Run CLI using 64-bit venv
run64:
	@echo "🚀 Running CLI using .venv64..."
	.venv64/Scripts/$(CLI) $(ARGS)

# Delete both virtual environments
clean:
	@echo "🧹 Cleaning up..."
	@if [ -d ".venv32" ]; then rm -rf .venv32; fi
	@if [ -d ".venv64" ]; then rm -rf .venv64; fi
	@find src -type d -name "__pycache__" -exec rm -rf {} +
