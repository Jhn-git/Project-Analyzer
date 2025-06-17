#!/usr/bin/env python3
import sys
import os

# Add the Project-Analyzer directory to the Python path to recognize the 'analyzer' package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer.main import main

if __name__ == "__main__":
    main()
