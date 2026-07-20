"""Regenerate the royalty-free placeholder WAV files using the standard library."""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import wave

RATE = 22_050
ROOT = Path(__file__).resolve().parent


def envelope(position: int, total: int, attack: float = .03, release: float = .18) -> float:
    t = position / RATE; duration = total / RATE
    return min(1.0, t / max(.001, attack), (duration - t) / max(.001, release))


def write_wave(name: str, seconds: float, sample) -> None:
    total = int(RATE * seconds); values = array("h")
    for index in range(total):
        value = max(-1.0, min(1.0, sample(index, total)))
        values.append(round(value * 16_000))
    with wave.open(str(ROOT / name), "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(RATE)
        output.writeframes(values.tobytes())


def build() -> None:
    write_wave("boundary.wav", .48, lambda i, n: (
        math.sin(math.tau * 440 * i / RATE) + .55 * math.sin(math.tau * 660 * i / RATE)
    ) * .55 * envelope(i, n, .012, .24))
    rng = random.Random(2026)
    noise = [rng.uniform(-1, 1) for _ in range(int(RATE * 2.4))]
    write_wave("six.wav", 1.25, lambda i, n: (noise[i] * .30 + math.sin(math.tau * 180 * i / RATE) * .10)
               * envelope(i, n, .08, .40))
    write_wave("wicket.wav", .72, lambda i, n: math.sin(math.tau * (115 - 60 * i / n) * i / RATE)
               * math.exp(-5.2 * i / n))
    write_wave("close_call.wav", .65, lambda i, n: (noise[i] * .12 + math.sin(math.tau * (210 + 90*i/n) * i / RATE) * .08)
               * envelope(i, n, .06, .24))
    write_wave("applause.wav", 2.0, lambda i, n: noise[i] * (.18 + .10 * math.sin(math.tau * 7 * i / RATE))
               * envelope(i, n, .16, .38))


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    build()
    print("Generated:", ", ".join(path.name for path in sorted(ROOT.glob("*.wav"))))
