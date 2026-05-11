#!/usr/bin/env python3
# home_manager.py - thin wrapper入口，重定向到 home_manager 包
import sys
import os

# 添加父目录到 sys.path，确保能找到 home_manager 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from home_manager.home_manager import main

if __name__ == "__main__":
    sys.exit(main())
