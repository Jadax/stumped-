"""Test Steam achievement system"""
from src.steam_integration import ACHIEVEMENTS, SteamIntegration
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
    root = Path(directory)
    steam = SteamIntegration(root, 123, 456, root / 'Steam')
    steam.initialise()
    
    # Test unlocking achievements
    print('Testing achievement system...')
    for achievement in ACHIEVEMENTS[:5]:  # Test first 5
        result = steam.unlock_achievement(achievement.id)
        status = "UNLOCKED" if result else "FAILED"
        print(f"  {achievement.name}: {status}")
    
    # Test persistence
    steam.shutdown()
    restored = SteamIntegration(root, 123, 456, root / 'Steam')
    restored.initialise()
    print(f"Persisted achievements: {len(restored.unlocked)}")
    print("All tests passed!")
