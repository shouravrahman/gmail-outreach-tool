"""
Entry point for the Bulk Email Tool.
Redirects to the main dashboard logic in src/utils/dashboard.py
"""

import sys
import os

# Add the current directory to sys.path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.dashboard import main

if __name__ == "__main__":
    main()
