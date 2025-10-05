#!/usr/bin/env python3
"""
Telegram Fact-Checker Bot - Entry Point
Точка входа для совместимости с workflow
"""

from app.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
