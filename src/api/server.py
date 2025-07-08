# src/api/server.py
# V2: Fügt einen Endpunkt zum Starten von Simulationen hinzu und verwaltet die Spielsitzung.

import logging
import uvicorn
import random
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Projektinterne Imports
from src.game_logic.game_state_manager import GameStateManager
from src.definitions.loader import load_character_templates
from src.ui.cli_output_adapter import CliOutputAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

game_session: Dict[str, Optional[GameStateManager]] = {"current": None}
CHARACTER_TEMPLATES = load_character_templates()
AVAILABLE_HERO_IDS = list(CHARACTER_TEMPLATES.keys())

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server startet... Ressourcen werden durch Manager geladen.")
    yield
    logger.info("Server fährt herunter.")

app = FastAPI(
    title="Python RPG Backend",
    description="Dieser Server stellt die Spiellogik für den Godot-Client bereit.",
    version="0.6.0",
    lifespan=lifespan
)

class SimulationStartRequest(BaseModel):
    hero_id: str

def get_current_state_dict() -> Dict[str, Any]:
    gsm = game_session.get("current")
    if not gsm:
        return {"error": "No active simulation."}

    map_data = gsm.map_manager.get_map_data()
    char_list = []
    for char_id, char_instance in gsm.character_manager.active_characters.items():
        char_list.append({
            "id": char_instance.instance_id,
            "name": char_instance.name,
            "class_id": char_instance.base_template.id,
            "asset_key": getattr(char_instance.base_template, 'asset_key', None),
            "level": char_instance.level,
            "hp": char_instance.current_hp,
            "max_hp": char_instance.max_hp,
            "position": getattr(char_instance, 'position', None)
        })
    return {"map": map_data, "characters": char_list}

@app.get("/", tags=["Status"])
def read_root():
    return {"status": "Python RPG Backend is running"}

@app.post("/simulation/start", tags=["Game Control"])
def start_new_simulation(request: SimulationStartRequest):
    hero_id = request.hero_id
    logger.info(f"Anfrage zum Starten einer neuen Simulation für Held: '{hero_id}'")

    if hero_id == "random":
        hero_id = random.choice(AVAILABLE_HERO_IDS)
        logger.info(f"Zufälliger Held ausgewählt: '{hero_id}'")

    if hero_id not in AVAILABLE_HERO_IDS:
        raise HTTPException(status_code=404, detail=f"Heldenklasse '{hero_id}' nicht gefunden.")
    
    try:
        output_adapter = CliOutputAdapter()
        game_session["current"] = GameStateManager(hero_id=hero_id, output_logger=output_adapter)
        logger.info(f"Neue Simulation erfolgreich für '{hero_id}' initialisiert.")
        return get_current_state_dict()
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung des GameStateManager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fehler bei der Initialisierung der Spielwelt.")

@app.get("/state", tags=["Game State"])
def get_full_game_state():
    if game_session.get("current") is None:
        raise HTTPException(status_code=404, detail="Keine aktive Simulation. Bitte zuerst mit /simulation/start eine starten.")
    return get_current_state_dict()

@app.post("/tick", tags=["Game State"])
def advance_game_tick():
    gsm = game_session.get("current")
    if gsm is None:
        raise HTTPException(status_code=404, detail="Keine aktive Simulation. Bitte zuerst mit /simulation/start eine starten.")
    
    if gsm.simulation_is_over:
        return {"message": "Simulation ist bereits beendet.", "final_state": get_current_state_dict()}

    gsm.tick()
    return get_current_state_dict()

def start_server():
    import nest_asyncio
    from pyngrok import ngrok

    port = 8000
    try:
        for tunnel in ngrok.get_tunnels():
            ngrok.disconnect(tunnel.public_url)
    except Exception as e:
        logger.warning(f"Konnte alte ngrok-Tunnel nicht schließen (ignoriert): {e}")
        
    public_url = ngrok.connect(port)
    logger.info(f"ngrok-Tunnel aktiv! Öffentliche URL: {public_url}")
    print(f"Server ist jetzt öffentlich erreichbar unter: {public_url}")

    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    start_server()