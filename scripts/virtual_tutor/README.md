# Virtual Tutor server and UI consolidation

This repository now ships a single FastAPI server that serves two UI variants—**new_ui** and **ui (legacy)**—from one application. All earlier experimental UI bundles (dummy/moral variants) were removed to simplify maintenance. Below is a detailed breakdown of the current layout, behavior, and testing strategy.

## What changed
- **Unified server**: `src/unified_server.py` hosts every HTTP route and websocket endpoint used by both UIs. The old `src/bica_server.py` and `src/new_ui/server.py` now just import this app when launched directly.
- **Two mounted UIs**: The new React-less bundle lives under `/new` (and also `/static` for compatibility). The legacy UI is mounted under `/legacy`. Static assets are served straight from `src/new_ui/static` and `src/ui` respectively.
- **Common API surface**:
  - Theme management: `POST /set_theme`, `GET /get_theme`, and `GET /get_theme_to_bica` share a single in-memory theme value.
  - Essay queueing: `POST /essay_data/` enqueues text submissions; `GET /get_data/` pops the next entry with metadata.
  - Chat history: `POST /chat/messages` appends messages; `GET /chat/messages` returns the collected list.
  - Recording status: `/start_recording` and `/stop_recording` emit websocket commands to the `local` client; `/is_processing_done` reflects the last recording notification.
  - Websockets: `/wss/{client_type}` receives status pings from the new UI, while `/legacy/wss/{client_id}` echoes tutor replies back to the legacy UI.
- **Legacy UI wiring**: `src/ui/script.js` points its websocket connection at `/legacy/wss` so it talks to the unified server.
- **Housekeeping**: Removed the `ui_dummy_*` and `ui_moral_*` directories to leave only the supported UI bundles.

## Running the server
```bash
# From scripts/virtual_tutor/src
uvicorn unified_server:app --reload --host 0.0.0.0 --port 5050
```

### Entry points
- `python bica_server.py` and `python new_ui/server.py` both import `unified_server.app`, so either command starts the same FastAPI application.

### UI paths
- New UI: http://localhost:5050/new or http://localhost:5050/static
- Legacy UI: http://localhost:5050/legacy

## Testing
Automated coverage lives in `tests/test_unified_server.py` and exercises:
- Static mounts for both UI bundles
- Theme round-tripping
- Chat storage
- Essay enqueue/dequeue flow
- Recording status websocket updates
- Legacy websocket echo behavior

Run with:
```bash
pytest scripts/virtual_tutor/tests/test_unified_server.py
```

> Note: The tests rely on `fastapi` and `uvicorn`. Install them with `pip install -r requirements.txt` (if available) or `pip install fastapi uvicorn`.
