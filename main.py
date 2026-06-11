"""
main.py — Vantavail Secure Chat Automation Bot Entry Point
SILENT MODE - No terminal output, all UI based.
"""

import os
# Suppress Qt font warnings on Windows
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false"

import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow


def main():
    """Main entry point - starts the UI only, no terminal output."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Create asyncio loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Create main window
    window = MainWindow(loop)
    window.show()
    
    # Start asyncio loop in separate thread
    import threading
    def run_loop():
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except Exception:
            pass
            
    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()