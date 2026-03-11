# Setup Scripts and Inventory Stats View

## Overview

Added the requested setup & run scripts and the Inventory Stats View to provide an overall view of sold and restocked items.

## 1. Setup & Run Scripts

Created easy-to-use batch/shell scripts for both Windows and Linux to streamline the virtual environment setup and execution process.

- [setup.bat](file:///home/yeager/Public/OSPOS/setup.bat) (Windows) / [setup.sh](file:///home/yeager/Public/OSPOS/setup.sh) (Linux): Creates the `.venv`, activates it, installs dependencies from [requirements.txt](file:///home/yeager/Public/OSPOS/requirements.txt), and runs backend migrations.
- [run.bat](file:///home/yeager/Public/OSPOS/run.bat) (Windows) / [run.sh](file:///home/yeager/Public/OSPOS/run.sh) (Linux): Checks if the `.venv` exists, activates it, and runs the Django server on `0.0.0.0:8002`.
