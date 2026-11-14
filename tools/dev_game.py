"""Opens the real game on screen in debug mode, running straight from mod/, so generate.py's GUI and text changes show without a restart.

py -3 tools/dev_game.py
It has its own settings folder, outside sweep.WORK, so the tuner shows it as the player's game and never stops it."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import observe
import sweep

ROOT = Path(__file__).resolve().parent.parent
USER = sweep.WORK.parent / "dev_user"
SAVES = ("seed_1", "full3_b_big3_1_1916", "soft1_b_soft_1_1916", "soft1_b_soft_1_1926")   # the start, and years with Bad Debts about

(USER / "save games").mkdir(parents=True, exist_ok=True)
for name in SAVES:
    shutil.copy(sweep.SAVES / f"{name}.v3", USER / "save games")
(USER / "content_load.json").write_text(json.dumps({"enabledMods": [{"path": str(ROOT / "mod")}], "disabledDLC": [], "enabledUGC": []}))
shutil.copy(observe.DOCS / "pdx_settings.json", USER)
subprocess.Popen([str(observe.GAME / "victoria3.exe"), "-gdpr-compliant", "-debug_mode", f"-userdir={USER}"], cwd=str(observe.GAME),
                 env={**os.environ, "SteamAppId": observe.STEAM_APP_ID, "SteamGameId": observe.STEAM_APP_ID})
print("opening the game, settings in", USER)
