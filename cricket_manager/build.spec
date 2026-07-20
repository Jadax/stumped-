# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file Windows build for Stumped!."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH)

hidden_imports = sorted(set(
    collect_submodules("pygame_gui")
    + collect_submodules("pygame")
    + [
        "sqlite3", "json", "logging.handlers", "tkinter", "tkinter.messagebox",
        "ui.dashboard", "ui.squad", "ui.selection", "ui.pre_match",
        "ui.match_view", "ui.inbox", "ui.transfers", "ui.training",
        "ui.finances", "ui.youth", "ui.facilities", "ui.settings",
        "src.views.splash_screen", "src.utilities.logger",
        "src.controllers.audio_controller",
        "src.controllers.game_controller", "src.models.manager",
        "src.models.difficulty", "src.models.currency",
        "src.utilities.player_portraits", "src.utilities.logo_generator",
        "src.views.screens.main_menu", "src.views.screens.new_game_setup",
        "src.views.screens.career_team_selection", "src.views.screens.world_cup_setup",
        "src.views.screens.tournament_setup",
        "src.views.screens.help_screen", "src.utilities.graphics",
        "src.steam_integration",
    ]
))

asset_datas = []
for asset in (ROOT / "assets").rglob("*"):
    if asset.is_file() and asset.name.lower() != "music.wav":
        destination = Path("assets") / asset.relative_to(ROOT / "assets").parent
        asset_datas.append((str(asset), str(destination)))

datas = [
    (str(ROOT / "config.json"), "."),
    (str(ROOT / "ui" / "theme.json"), "ui"),
    (str(ROOT / "src" / "data"), "src/data"),
    # Preserve empty writable-folder structure without shipping a developer save.
    (str(ROOT / "data" / ".gitkeep"), "data"),
    (str(ROOT / "logs" / ".gitkeep"), "logs"),
] + asset_datas

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[str(ROOT / "hooks")],
    runtime_hooks=[str(ROOT / "hooks" / "pyi_rth_stumped.py")],
    excludes=["pytest", "numpy.tests", "PIL.ImageQt"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Stumped",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",
    icon=str(ROOT / "assets" / "images" / "icon.ico"),
    version=str(ROOT / "version_info.txt"),
    uac_admin=False,
)
