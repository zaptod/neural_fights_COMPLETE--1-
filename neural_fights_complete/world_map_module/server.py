"""
NEURAL FIGHTS — 3D Globe API Server
Serves world_state.json, gods.json, and world_regions.json to the Three.js globe.
Runs on localhost:7331. Launched by run_worldmap.py.
"""
import json
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Server] Could not load {filename}: {e}")
        return {}


# ── Static Files ──────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "globe.html")

@app.route("/globe.html")
def globe():
    return send_from_directory(BASE_DIR, "globe.html")


# ── API Endpoints ─────────────────────────────────────────────────

@app.route("/api/state")
def api_state():
    """Live world state — zone ownership, contested borders, ancient seals."""
    return jsonify(load_json("world_state.json"))


@app.route("/api/gods")
def api_gods():
    """All registered gods and their stats."""
    return jsonify(load_json("gods.json"))


@app.route("/api/regions")
def api_regions():
    """World geography — all 27 zones with polygon vertices."""
    raw = load_json("world_regions.json")
    # Reshape from list of regions to dict keyed by region_id
    result = {}
    for region in raw.get("regions", []):
        result[region["region_id"]] = region
    return jsonify(result)


@app.route("/api/full")
def api_full():
    """Single endpoint returning everything — for initial load."""
    return jsonify({
        "state":   load_json("world_state.json"),
        "gods":    load_json("gods.json"),
        "regions": load_json("world_regions.json"),
    })


# ── Write Endpoints (for future God Wizard integration) ───────────

@app.route("/api/claim/<zone_id>/<god_id>", methods=["POST"])
def claim_zone(zone_id, god_id):
    """Claim a zone for a god. Updates world_state.json."""
    try:
        state_path = os.path.join(DATA_DIR, "world_state.json")
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        state["zone_ownership"][zone_id] = god_id

        # Update god's owned_zones in gods.json
        gods_path = os.path.join(DATA_DIR, "gods.json")
        with open(gods_path, "r", encoding="utf-8") as f:
            gods = json.load(f)

        for god in gods.get("gods", []):
            if god["god_id"] == god_id:
                if zone_id not in god.get("owned_zones", []):
                    god.setdefault("owned_zones", []).append(zone_id)
            else:
                # Remove from other gods
                if zone_id in god.get("owned_zones", []):
                    god["owned_zones"].remove(zone_id)

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        with open(gods_path, "w", encoding="utf-8") as f:
            json.dump(gods, f, indent=2, ensure_ascii=False)

        return jsonify({"ok": True, "zone": zone_id, "god": god_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("[Neural Fights] Globe server starting on http://localhost:7331")
    print("[Neural Fights] Open your browser to http://localhost:7331")
    app.run(host="127.0.0.1", port=7331, debug=False, threaded=True)
