"""
NEURAL FIGHTS — World Map Launcher (3D Globe Edition)
Starts the Flask API server and opens the holographic globe in the browser.

Usage:
  python run_worldmap.py
  python run_worldmap.py --port 8080
  python run_worldmap.py --no-browser   (server only, open manually)
"""
import sys
import os
import time
import socket
import argparse
import threading
import webbrowser
import subprocess


def parse_args():
    p = argparse.ArgumentParser(description="Neural Fights — 3D Globe Map Server")
    p.add_argument("--port",       type=int, default=7331, help="Server port (default: 7331)")
    p.add_argument("--no-browser", action="store_true",   help="Start server without opening browser")
    return p.parse_args()


def wait_for_server(port, timeout=12):
    """Poll until the Flask server is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def check_flask():
    """Check if Flask and flask-cors are installed."""
    missing = []
    try:
        import flask
    except ImportError:
        missing.append("flask")
    try:
        import flask_cors
    except ImportError:
        missing.append("flask-cors")
    return missing


def install_deps(missing):
    """Offer to auto-install missing packages."""
    print(f"[WorldMap] Missing packages: {', '.join(missing)}")
    ans = input("Install them now? [y/N]: ").strip().lower()
    if ans == 'y':
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        return True
    return False


def run_server(port):
    """Run the Flask server in the current thread."""
    # Patch the port into server.py at runtime
    import importlib, sys as _sys
    server_dir = os.path.dirname(os.path.abspath(__file__))
    if server_dir not in _sys.path:
        _sys.path.insert(0, server_dir)

    # Patch port via env so server.py can pick it up
    os.environ["WORLDMAP_PORT"] = str(port)

    from flask import Flask, jsonify, send_from_directory
    from flask_cors import CORS
    import json

    app = Flask(__name__, static_folder=server_dir)
    CORS(app)

    DATA_DIR = os.path.join(server_dir, "data")

    def load_json(filename):
        try:
            with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Server] Load error {filename}: {e}")
            return {}

    @app.route("/")
    @app.route("/globe.html")
    def globe():
        return send_from_directory(server_dir, "globe.html")

    @app.route("/api/state")
    def api_state():
        return jsonify(load_json("world_state.json"))

    @app.route("/api/gods")
    def api_gods():
        return jsonify(load_json("gods.json"))

    @app.route("/api/regions")
    def api_regions():
        raw = load_json("world_regions.json")
        result = {r["region_id"]: r for r in raw.get("regions", [])}
        return jsonify(result)

    @app.route("/api/full")
    def api_full():
        return jsonify({
            "state":   load_json("world_state.json"),
            "gods":    load_json("gods.json"),
            "regions": load_json("world_regions.json"),
        })

    @app.route("/api/claim/<zone_id>/<god_id>", methods=["POST"])
    def claim_zone(zone_id, god_id):
        try:
            state_path = os.path.join(DATA_DIR, "world_state.json")
            gods_path  = os.path.join(DATA_DIR, "gods.json")

            with open(state_path, "r", encoding="utf-8") as f: state = json.load(f)
            with open(gods_path,  "r", encoding="utf-8") as f: gods  = json.load(f)

            state["zone_ownership"][zone_id] = god_id
            for god in gods.get("gods", []):
                if god["god_id"] == god_id:
                    if zone_id not in god.get("owned_zones", []):
                        god.setdefault("owned_zones", []).append(zone_id)
                else:
                    if zone_id in god.get("owned_zones", []):
                        god["owned_zones"].remove(zone_id)

            with open(state_path, "w", encoding="utf-8") as f: json.dump(state, f, indent=2)
            with open(gods_path,  "w", encoding="utf-8") as f: json.dump(gods,  f, indent=2)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)   # Suppress Flask request noise

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)


def main():
    args = parse_args()
    port = args.port

    print("=" * 56)
    print("  ⚔  NEURAL FIGHTS — AETHERMOOR GLOBE  ⚔")
    print("=" * 56)

    # Check dependencies
    missing = check_flask()
    if missing:
        if not install_deps(missing):
            print(f"[WorldMap] Install manually: pip install {' '.join(missing)}")
            sys.exit(1)

    print(f"[WorldMap] Starting globe server on port {port}...")

    # Start Flask in a daemon thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for the server to come up
    if not wait_for_server(port, timeout=10):
        print(f"[WorldMap] ERROR: Server did not start in time on port {port}")
        sys.exit(1)

    url = f"http://localhost:{port}"
    print(f"[WorldMap] Globe is live at: {url}")

    if not args.no_browser:
        print(f"[WorldMap] Opening browser...")
        webbrowser.open(url)

    print("[WorldMap] Press Ctrl+C to stop the server.\n")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WorldMap] Shutting down. The Gods will wait.")


if __name__ == "__main__":
    main()
