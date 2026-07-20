"""Deterministic, original player portraits rendered entirely with Pygame.

No photographs or third-party likenesses are used.  A player's ID seeds facial
geometry, colouring, hair, and kit details, so the same player remains visually
recognisable across saves and screens while every generated squad is diverse.
"""
from __future__ import annotations

from functools import lru_cache
import random
import pygame


TONE_RANGES = {
    "england": ((238, 196, 164), (177, 121, 91)),
    "australia": ((236, 190, 151), (168, 109, 78)),
    "new zealand": ((225, 175, 139), (153, 101, 73)),
    "india": ((196, 132, 86), (104, 63, 42)),
    "pakistan": ((202, 143, 96), (107, 68, 46)),
    "bangladesh": ((190, 126, 80), (100, 61, 40)),
    "sri lanka": ((183, 115, 72), (88, 51, 35)),
    "south africa": ((209, 154, 111), (72, 43, 31)),
    "west indies": ((132, 82, 58), (54, 33, 27)),
    "afghanistan": ((196, 137, 91), (101, 62, 42)),
    "zimbabwe": ((145, 89, 59), (58, 35, 28)),
}


def _key(country: str) -> str:
    value = country.lower().replace("english", "england").replace("australian", "australia")
    for candidate in TONE_RANGES:
        if candidate in value:
            return candidate
    return "england"


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


@lru_cache(maxsize=1024)
def generate_portrait(country: str, age: int, player_id: int, size: int = 128) -> pygame.Surface:
    """Return a copyright-safe head-and-shoulders portrait with transparent edges."""
    rng = random.Random(f"portrait:{player_id}:{country}:{age}")
    canvas = pygame.Surface((128, 128), pygame.SRCALPHA)
    lo, hi = TONE_RANGES[_key(country)]
    skin = _mix(lo, hi, rng.random())
    shadow = _mix(skin, (40, 24, 20), .24)
    hair = rng.choice([(28, 22, 19), (47, 31, 22), (72, 48, 31), (112, 77, 47)])
    kit = rng.choice([(35, 134, 54), (29, 78, 137), (157, 45, 53), (231, 169, 31)])

    # Shoulders, neck and ears establish a clean editorial headshot silhouette.
    pygame.draw.ellipse(canvas, kit, (12, 91, 104, 54))
    pygame.draw.rect(canvas, shadow, (51, 78, 27, 27), border_radius=8)
    face_w = rng.randint(55, 64); face_h = rng.randint(72, 80)
    face = pygame.Rect(64 - face_w // 2, 15, face_w, face_h)
    pygame.draw.ellipse(canvas, shadow, face.move(2, 3))
    pygame.draw.ellipse(canvas, skin, face)
    pygame.draw.ellipse(canvas, skin, (face.x - 5, 47, 11, 22))
    pygame.draw.ellipse(canvas, skin, (face.right - 6, 47, 11, 22))

    # Hairline and style vary deterministically. Older players may show grey.
    if age >= 34 and rng.random() < min(.75, (age - 31) / 16):
        hair = _mix(hair, (170, 170, 166), rng.uniform(.35, .75))
    style = rng.randrange(4)
    if style == 0:
        pygame.draw.polygon(canvas, hair, [(face.x + 3, face.y + 21), (face.x + 8, face.y - 3),
                                           (face.right - 8, face.y - 2), (face.right - 2, face.y + 18),
                                           (face.centerx, face.y + 11)])
    elif style == 1:
        pygame.draw.ellipse(canvas, hair, (face.x + 2, face.y - 7, face.width - 4, 28))
        pygame.draw.rect(canvas, hair, (face.x + 1, face.y + 7, 8, 28), border_radius=4)
    elif style == 2:
        for x in range(face.x + 3, face.right - 2, 7):
            pygame.draw.circle(canvas, hair, (x, face.y + rng.randint(1, 8)), 7)
    else:
        pygame.draw.polygon(canvas, hair, [(face.x + 2, face.y + 19), (face.x + 8, face.y - 4),
                                           (face.right - 4, face.y + 1), (face.right - 1, face.y + 21)])

    eye_y = face.y + 35; eye_dx = rng.randint(12, 15)
    for x in (64 - eye_dx, 64 + eye_dx):
        pygame.draw.ellipse(canvas, (245, 244, 236), (x - 5, eye_y - 2, 10, 6))
        pygame.draw.circle(canvas, rng.choice([(45, 31, 25), (62, 74, 53), (44, 57, 74)]), (x, eye_y + 1), 2)
    pygame.draw.line(canvas, shadow, (64, eye_y + 4), (61 + rng.randint(0, 6), eye_y + 20), 2)
    mouth_y = eye_y + 29
    pygame.draw.line(canvas, shadow, (56, mouth_y), (72, mouth_y + rng.choice([-1, 0, 1])), 2)

    beard_chance = .08 if age < 20 else .40 if age < 31 else .58
    if rng.random() < beard_chance:
        beard = _mix(hair, skin, .24)
        pygame.draw.arc(canvas, beard, (face.x + 7, face.y + 31, face.width - 14, face.height - 25),
                        3.20, 6.18, rng.randint(2, 4))
        if rng.random() < .55:
            pygame.draw.line(canvas, beard, (58, mouth_y - 4), (70, mouth_y - 4), 2)
    if age >= 38:
        for offset in (-9, 9):
            pygame.draw.line(canvas, _mix(skin, (92, 73, 63), .3),
                             (64 + offset - 4, eye_y + 8), (64 + offset + 4, eye_y + 8), 1)

    # Scale once for the requesting widget; the transparent background lets the
    # portrait sit naturally in every card and modal.
    return pygame.transform.smoothscale(canvas, (size, size)) if size != 128 else canvas


_legacy_generate_portrait = generate_portrait


class PlayerPortraitGenerator:
    """Supersampled editorial portraits with country and age variation.

    These are stylised fictional people, not synthetic photographs or real
    likenesses. Rendering at 3x and reducing once produces clean edges at 4K.
    """

    country_parameters = {
        key: {"skin_tones": value, "dark_hair_bias": .78 if key not in {"england", "australia", "new zealand"} else .48}
        for key, value in TONE_RANGES.items()
    }

    def generate(self, country: str, age: int, player_id: int, size: int = 128) -> pygame.Surface:
        size = max(24, int(size)); scale = 3
        width = size * scale
        rng = random.Random(f"portrait-v2:{player_id}:{country}:{age}")
        canvas = pygame.Surface((width, width), pygame.SRCALPHA)
        u = lambda value: round(value * width / 128)
        key = _key(country); light, dark = TONE_RANGES[key]
        skin = _mix(light, dark, rng.uniform(.05, .95))
        shade = _mix(skin, (38, 25, 23), .22)
        highlight = _mix(skin, (255, 238, 216), .18)
        hair_palette = [(25, 20, 18), (46, 31, 23), (78, 49, 31), (126, 86, 52), (170, 132, 84)]
        params = self.country_parameters.get(key, self.country_parameters["england"])
        hair = rng.choice(hair_palette[:3] if rng.random() < params["dark_hair_bias"] else hair_palette)
        if age >= 34 and rng.random() < min(.78, (age - 30) / 18):
            hair = _mix(hair, (174, 174, 169), rng.uniform(.25, .72))
        kit = rng.choice([(46, 160, 67), (42, 105, 184), (190, 59, 66), (214, 154, 27), (92, 73, 176)])

        # A softly graded studio backdrop and rim light move the result away
        # from flat avatar art while remaining entirely procedural/original.
        for radius in range(62, 8, -3):
            amount = (62 - radius) / 54
            colour = _mix((22, 30, 42), (53, 65, 78), amount * .55)
            pygame.draw.circle(canvas, colour, (u(64), u(61)), u(radius))

        # Bust and neck.
        pygame.draw.ellipse(canvas, _mix(kit, (10, 15, 22), .18), (u(8), u(91), u(112), u(58)))
        pygame.draw.ellipse(canvas, kit, (u(14), u(96), u(100), u(48)))
        pygame.draw.rect(canvas, shade, (u(50), u(77), u(28), u(29)), border_radius=u(8))

        face_w, face_h = rng.randint(55, 65), rng.randint(71, 81)
        fx, fy = 64 - face_w // 2, rng.randint(14, 17)
        jaw = [(u(fx + 5), u(fy + 8)), (u(fx + face_w - 5), u(fy + 8)),
               (u(fx + face_w), u(fy + 43)), (u(fx + face_w - 11), u(fy + face_h - 7)),
               (u(64), u(fy + face_h)), (u(fx + 10), u(fy + face_h - 7)), (u(fx), u(fy + 43))]
        pygame.draw.polygon(canvas, shade, [(x + u(2), y + u(3)) for x, y in jaw])
        pygame.draw.polygon(canvas, skin, jaw)
        pygame.draw.ellipse(canvas, skin, (u(fx - 5), u(fy + 32), u(11), u(23)))
        pygame.draw.ellipse(canvas, skin, (u(fx + face_w - 6), u(fy + 32), u(11), u(23)))
        pygame.draw.ellipse(canvas, highlight, (u(fx + 10), u(fy + 11), u(face_w // 3), u(face_h // 2)))

        # Layered translucent planes mimic studio portrait lighting: temple
        # fall-off, cheek volume, jaw shadow and a narrow nose highlight.
        lighting = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        pygame.draw.ellipse(lighting, (*shade, 72), (u(fx + face_w * .53), u(fy + 8), u(face_w * .43), u(face_h * .72)))
        pygame.draw.ellipse(lighting, (*highlight, 58), (u(fx + 8), u(fy + 24), u(face_w * .42), u(face_h * .34)))
        pygame.draw.ellipse(lighting, (*shade, 54), (u(fx + 9), u(fy + face_h * .66), u(face_w - 18), u(face_h * .25)))
        pygame.draw.ellipse(lighting, (*highlight, 44), (u(61), u(fy + 25), u(7), u(32)))
        canvas.blit(lighting, (0, 0))

        # Fine, deterministic skin texture prevents large areas reading as
        # plastic blocks after upscaling. Points are deliberately low contrast.
        for _ in range(150):
            px, py = rng.randint(fx + 7, fx + face_w - 8), rng.randint(fy + 19, fy + face_h - 9)
            ellipse = ((px - 64) / max(1, face_w * .50)) ** 2 + ((py - (fy + face_h * .52)) / max(1, face_h * .54)) ** 2
            if ellipse <= 1:
                pore = _mix(skin, highlight if rng.random() < .47 else shade, rng.uniform(.08, .18))
                pygame.draw.circle(canvas, pore, (u(px), u(py)), max(1, u(.32)))

        # Hair styles are age-appropriate; youth facial hair is intentionally rare.
        style = rng.randrange(5)
        if style in {0, 1}:
            pygame.draw.ellipse(canvas, hair, (u(fx + 1), u(fy - 7), u(face_w - 2), u(29)))
            if style == 1: pygame.draw.rect(canvas, hair, (u(fx), u(fy + 5), u(8), u(25)), border_radius=u(3))
        elif style == 2:
            for x in range(fx + 3, fx + face_w - 2, 6):
                pygame.draw.circle(canvas, hair, (u(x), u(fy + rng.randint(0, 8))), u(7))
        elif style == 3:
            pygame.draw.polygon(canvas, hair, [(u(fx + 1),u(fy + 20)),(u(fx + 8),u(fy - 5)),(u(fx + face_w - 4),u(fy)),(u(fx + face_w),u(fy + 20)),(u(64),u(fy + 10))])
        else:
            pygame.draw.arc(canvas, hair, (u(fx + 3),u(fy - 2),u(face_w - 6),u(30)), 3.1, 6.2, u(7))

        eye_y, eye_dx = fy + 35, rng.randint(12, 15)
        eye_colour = rng.choice([(43, 30, 24), (57, 72, 51), (48, 62, 82)])
        for x in (64 - eye_dx, 64 + eye_dx):
            pygame.draw.ellipse(canvas, _mix((242, 239, 229), skin, .18), (u(x - 5), u(eye_y - 2), u(10), u(5)))
            pygame.draw.circle(canvas, eye_colour, (u(x), u(eye_y)), u(1.8))
            pygame.draw.circle(canvas, (18, 18, 17), (u(x), u(eye_y)), max(1, u(.75)))
            pygame.draw.circle(canvas, (235, 238, 230), (u(x - .6), u(eye_y - .7)), max(1, u(.3)))
            pygame.draw.arc(canvas, shade, (u(x - 6), u(eye_y - 4), u(12), u(7)), 3.25, 6.05, u(1))
            pygame.draw.line(canvas, _mix(hair, skin, .18), (u(x - 6), u(eye_y - 7)), (u(x + 5), u(eye_y - 7)), u(1.4))
        nose_x = 61 + rng.randint(0, 6)
        pygame.draw.line(canvas, _mix(shade, skin, .22), (u(64),u(eye_y + 5)),(u(nose_x),u(eye_y + 20)),u(1.2))
        pygame.draw.arc(canvas, shade, (u(59),u(eye_y + 15),u(11),u(8)), .2, 2.9, u(1))
        mouth_y = eye_y + 29
        lip = _mix(skin, (118, 50, 50), .32)
        pygame.draw.arc(canvas, lip, (u(55),u(mouth_y - 3),u(18),u(7)), .10, 3.03, u(1.2))
        pygame.draw.arc(canvas, _mix(lip, shade, .22), (u(56),u(mouth_y - 1),u(16),u(7)), 3.25, 6.05, u(1.3))

        beard_chance = .03 if age < 19 else .34 if age < 31 else .55
        if rng.random() < beard_chance:
            beard = _mix(hair, skin, .20)
            pygame.draw.arc(canvas, beard, (u(fx + 6),u(fy + 31),u(face_w - 12),u(face_h - 24)), 3.15, 6.2, u(rng.randint(2,4)))
            if rng.random() < .58: pygame.draw.line(canvas, beard, (u(57),u(mouth_y - 4)), (u(71),u(mouth_y - 4)), u(2))
            for _ in range(70):
                bx, by = rng.randint(fx + 9, fx + face_w - 10), rng.randint(mouth_y - 4, fy + face_h - 7)
                if abs(bx - 64) > (by - mouth_y) * .55 or by > mouth_y + 6:
                    pygame.draw.circle(canvas, _mix(beard, skin, .18), (u(bx), u(by)), max(1, u(.28)))
        if age >= 36:
            wrinkle = _mix(skin, (86, 68, 61), .35)
            for offset in (-10, 10): pygame.draw.line(canvas, wrinkle, (u(64 + offset - 4),u(eye_y + 8)),(u(64 + offset + 4),u(eye_y + 8)),u(1))
            if age >= 42: pygame.draw.arc(canvas, wrinkle, (u(53),u(mouth_y - 2),u(22),u(14)), .2, 2.9, u(1))
        return pygame.transform.smoothscale(canvas, (size, size))


_PORTRAIT_GENERATOR = PlayerPortraitGenerator()


@lru_cache(maxsize=2048)
def generate_portrait(country: str, age: int, player_id: int, size: int = 128) -> pygame.Surface:
    return _PORTRAIT_GENERATOR.generate(country, age, player_id, size)


def draw_portrait(surface: pygame.Surface, rect: pygame.Rect, player: dict) -> None:
    portrait = generate_portrait(str(player.get("nationality", "England")), int(player.get("age", 25)),
                                 int(player.get("id", 0)), min(rect.width, rect.height))
    destination = portrait.get_rect(center=pygame.Rect(rect).center)
    surface.blit(portrait, destination)
