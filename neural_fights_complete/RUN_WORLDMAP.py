"""
Neural Fights — World Map Launcher
Run this from the neural_fights_complete/ directory.
"""
import subprocess, sys, os
script = os.path.join(os.path.dirname(__file__), "world_map_module", "run_worldmap.py")
subprocess.run([sys.executable, script])
