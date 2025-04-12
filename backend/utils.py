import os
import sys
import platform
import subprocess
import logging
import socket
from contextlib import closing
import time
import json
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_free_port(start_port: int = 8001, end_port: int = 8100) -> int:
    """Find a free port within a range"""
    for port in range(start_port, end_port):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"No free ports in range {start_port}-{end_port}")

def start_backend_server(port: int = 8001):
    """Start the backend server if not running"""
    if is_port_in_use(port):
        logger.info(f"Backend already running on port {port}")
        return True
    
    logger.info(f"Starting backend server on port {port}")
    
    try:
        # Get the directory where the backend is located
        if getattr(sys, 'frozen', False):
            # Running in a bundle (PyInstaller)
            backend_dir = os.path.join(sys._MEIPASS, 'backend')
        else:
            # Running in normal Python environment
            backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
        
        # Start the backend server
        if platform.system() == 'Windows':
            subprocess.Popen(
                f'start "AI Document Assistant Backend" /B python -m uvicorn app:app --host 127.0.0.1 --port {port}',
                cwd=backend_dir,
                shell=True
            )
        else:  # macOS or Linux
            subprocess.Popen(
                f'python -m uvicorn app:app --host 127.0.0.1 --port {port} &',
                cwd=backend_dir,
                shell=True
            )
        
        # Wait for server to start
        for _ in range(10):
            time.sleep(1)
            if is_port_in_use(port):
                logger.info("Backend server started successfully")
                return True
        
        logger.error("Backend server failed to start")
        return False
    except Exception as e:
        logger.error(f"Error starting backend: {str(e)}")
        return False

def check_ollama_available() -> bool:
    """Check if Ollama is installed and available"""
    try:
        # Check if Ollama is in PATH
        if platform.system() == 'Windows':
            result = subprocess.run(["where", "ollama"], capture_output=True, text=True)
        else:  # macOS or Linux
            result = subprocess.run(["which", "ollama"], capture_output=True, text=True)
        
        return result.returncode == 0
    except Exception:
        return False

def setup_autostart() -> bool:
    """Set up the application to start with OS"""
    try:
        app_name = "ASHBORN AI"
        
        if platform.system() == 'Windows':
            # Get startup folder
            startup_folder = os.path.join(os.environ["APPDATA"], 
                                         "Microsoft", "Windows", "Start Menu", 
                                         "Programs", "Startup")
            
            # Create shortcut
            app_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            shortcut_path = os.path.join(startup_folder, f"{app_name}.lnk")
            
            # Create VBS script to make shortcut
            vbs_content = f"""
            Set WshShell = WScript.CreateObject("WScript.Shell")
            Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
            shortcut.TargetPath = "{app_path}"
            shortcut.WorkingDirectory = "{os.path.dirname(app_path)}"
            shortcut.Description = "{app_name}"
            shortcut.Save
            """
            
            # Write and execute VBS
            vbs_path = os.path.join(os.environ["TEMP"], "create_shortcut.vbs")
            with open(vbs_path, 'w') as f:
                f.write(vbs_content)
            
            subprocess.run(["cscript", vbs_path], check=True)
            os.remove(vbs_path)
            
        elif platform.system() == 'Darwin':  # macOS
            # Create launch agent plist
            plist_dir = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(plist_dir, exist_ok=True)
            
            plist_path = os.path.join(plist_dir, "com.aidocumentassistant.plist")
            app_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>com.aidocumentassistant</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{app_path}</string>
                </array>
                <key>RunAtLoad</key>
                <true/>
            </dict>
            </plist>
            """
            
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # Load the agent
            subprocess.run(["launchctl", "load", plist_path], check=True)
            
        else:  # Linux
            # Create desktop entry
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            
            desktop_path = os.path.join(autostart_dir, "ai-document-assistant.desktop")
            app_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            
            desktop_content = f"""[Desktop Entry]
            Type=Application
            Name=AI Document Assistant
            Exec={app_path}
            Terminal=false
            X-GNOME-Autostart-enabled=true
            """
            
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            
            # Make executable
            os.chmod(desktop_path, 0o755)
        
        return True
    except Exception as e:
        logger.error(f"Error setting up autostart: {str(e)}")
        return False

def remove_autostart() -> bool:
    """Remove application from autostart"""
    try:
        app_name = "AI Document Assistant"
        
        if platform.system() == 'Windows':
            # Remove from startup folder
            startup_folder = os.path.join(os.environ["APPDATA"], 
                                         "Microsoft", "Windows", "Start Menu", 
                                         "Programs", "Startup")
            shortcut_path = os.path.join(startup_folder, f"{app_name}.lnk")
            
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            
        elif platform.system() == 'Darwin':  # macOS
            # Remove launch agent plist
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.aidocumentassistant.plist")
            
            if os.path.exists(plist_path):
                subprocess.run(["launchctl", "unload", plist_path], check=True)
                os.remove(plist_path)
            
        else:  # Linux
            # Remove desktop entry
            desktop_path = os.path.expanduser("~/.config/autostart/ai-document-assistant.desktop")
            
            if os.path.exists(desktop_path):
                os.remove(desktop_path)
        
        return True
    except Exception as e:
        logger.error(f"Error removing autostart: {str(e)}")
        return False