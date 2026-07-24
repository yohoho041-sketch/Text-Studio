#!/usr/bin/env python3
import sys
import os

# Add local directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.app import SimpleJavaApp

def main():
    app = SimpleJavaApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
