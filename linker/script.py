# ============================================================
# linker/script.py - JSON Tabanli Linker Script Yukleyici
# ============================================================
# Cok basit bir linker script formati: JSON dosyasi.
# Memory bolgeleri ve hangi section'in hangi bolgeye gidecegini tarif eder.
# ============================================================

import json
import os


# Default script: tek 8KB bolge, .text + .data ayni RAM'de
DEFAULT_SCRIPT = {
    "memory": [
        {"name": "mem", "origin": 0, "length": 8192, "attrs": "rwx"}
    ],
    "sections": [
        {"name": ".text", "memory": "mem", "align": 4},
        {"name": ".data", "memory": "mem", "align": 4},
    ],
    "entry": 0,
}


def load_script(path=None):
    """Bir linker script JSON dosyasini yukler.

    path None ise default scripti doner.
    """
    if path is None:
        return dict(DEFAULT_SCRIPT)

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Linker script bulunamadi: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        script = json.load(f)

    validate_script(script)
    return script


def validate_script(script):
    """Linker script'in temel alanlarini dogrular."""
    if not isinstance(script, dict):
        raise ValueError("Script bir JSON object olmali")

    if "memory" not in script or not isinstance(script["memory"], list):
        raise ValueError("Script: 'memory' (list) gerekli")

    for mem in script["memory"]:
        for k in ("name", "origin", "length"):
            if k not in mem:
                raise ValueError(f"Memory bolgesinde '{k}' eksik")

    if "sections" not in script or not isinstance(script["sections"], list):
        raise ValueError("Script: 'sections' (list) gerekli")

    for sec in script["sections"]:
        for k in ("name", "memory"):
            if k not in sec:
                raise ValueError(f"Section'da '{k}' eksik: {sec}")
        if "align" not in sec:
            sec["align"] = 4

    return True


def get_memory(script, name):
    """Bir memory bolgesinin tanimini doner."""
    for m in script["memory"]:
        if m["name"] == name:
            return m
    return None


def get_section_memory(script, section_name):
    """Bir section'in atandigi memory bolgesinin adini doner."""
    for s in script["sections"]:
        if s["name"] == section_name:
            return s["memory"]
    return None


def get_section_align(script, section_name):
    """Bir section'in script'te tanimli hizalamasi."""
    for s in script["sections"]:
        if s["name"] == section_name:
            return s.get("align", 4)
    return 4
