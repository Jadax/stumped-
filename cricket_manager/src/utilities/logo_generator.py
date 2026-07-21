"""High-DPI procedural club crests made only from original geometry."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import pygame
from src.views.theme import get_font


def _palette(name: str) -> tuple[pygame.Color, pygame.Color, pygame.Color]:
    digest = hashlib.blake2b(name.encode("utf-8"), digest_size=12).digest()
    base = pygame.Color(34 + digest[0] % 100, 45 + digest[1] % 105, 55 + digest[2] % 100)
    accent = pygame.Color(125 + digest[3] % 115, 105 + digest[4] % 130, 35 + digest[5] % 150)
    return base, accent, pygame.Color("#f0f6fc")


class TeamLogoGenerator:
    """Generate stable shield, roundel, or crest marks from a club name."""

    @lru_cache(maxsize=256)
    def generate(self, team_name: str, size: int = 128, initials: str | None = None) -> pygame.Surface:
        size = max(24, int(size)); scale = 4; dim = size * scale
        image = pygame.Surface((dim, dim), pygame.SRCALPHA)
        primary, accent, white = _palette(team_name)
        digest = hashlib.sha256(team_name.encode("utf-8")).digest()
        mark = initials or "".join(word[0] for word in team_name.split()[:2])
        centre, radius = dim // 2, int(dim * .40)
        style = digest[7] % 3
        if style == 0:
            points = [(centre-radius, int(dim*.16)),(centre+radius,int(dim*.16)),
                      (centre+int(radius*.90),int(dim*.62)),(centre,int(dim*.91)),
                      (centre-int(radius*.90),int(dim*.62))]
            pygame.draw.polygon(image, primary, points)
            pygame.draw.polygon(image, accent, points, max(5, dim//34))
        elif style == 1:
            pygame.draw.aacircle(image, accent, (centre,centre), radius)
            pygame.draw.aacircle(image, primary, (centre,centre), int(radius*.82))
            pygame.draw.aacircle(image, white, (centre,centre), int(radius*.61), max(4,dim//60))
        else:
            points = [(centre,int(dim*.08)),(int(dim*.88),int(dim*.30)),(int(dim*.80),int(dim*.78)),
                      (centre,int(dim*.93)),(int(dim*.20),int(dim*.78)),(int(dim*.12),int(dim*.30))]
            pygame.draw.polygon(image, primary, points)
            pygame.draw.polygon(image, accent, points, max(5,dim//36))
        # Original cricket motif: seam ball crossing three stumps.
        for offset in (-int(dim*.13), 0, int(dim*.13)):
            pygame.draw.line(image, accent, (centre+offset,int(dim*.32)),(centre+offset,int(dim*.67)),max(5,dim//46))
        pygame.draw.line(image, accent,(int(dim*.33),int(dim*.32)),(int(dim*.67),int(dim*.32)),max(4,dim//60))
        pygame.draw.aacircle(image, white,(int(dim*.68),int(dim*.40)),int(dim*.09))
        pygame.draw.arc(image, accent,(int(dim*.61),int(dim*.32),int(dim*.14),int(dim*.16)),-1.1,1.1,max(3,dim//80))
        font = get_font(max(11, int(dim*.16)), bold=True)
        label = font.render(mark[:3].upper(), True, white)
        image.blit(label, label.get_rect(center=(centre,int(dim*.77))))
        return pygame.transform.smoothscale(image, (size,size))


TEAM_LOGOS = TeamLogoGenerator()


def draw_team_logo(surface: pygame.Surface, centre: tuple[int,int], size: int, team_name: str,
                   initials: str | None = None) -> None:
    logo = TEAM_LOGOS.generate(team_name, size, initials)
    surface.blit(logo, logo.get_rect(center=centre))
