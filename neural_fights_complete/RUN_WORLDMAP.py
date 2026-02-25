"""
Neural Fights — 3D Globe World Map Launcher
Opens the holographic Aethermoor globe in your browser.
Requires: pip install flask flask-cors
"""
import subprocess, sys, os
script = os.path.join(os.path.dirname(__file__), "world_map_module", "run_worldmap.py")
subprocess.run([sys.executable, script])
