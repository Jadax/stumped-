"""Crisp vector country flags drawn from public-domain national designs."""
from __future__ import annotations
import pygame

ALIASES={"English":"England","Australian":"Australia","Indian":"India","Pakistani":"Pakistan",
"South African":"South Africa","New Zealander":"New Zealand","West Indian":"West Indies"}
def draw_country_flag(surface:pygame.Surface, rect:pygame.Rect, country:str)->None:
    r=pygame.Rect(rect); country=ALIASES.get(country,country); pygame.draw.rect(surface,"#f0f6fc",r)
    if country=="India":
        pygame.draw.rect(surface,"#FF9933",(r.x,r.y,r.w,r.h//3)); pygame.draw.rect(surface,"#138808",(r.x,r.bottom-r.h//3,r.w,r.h//3)); pygame.draw.circle(surface,"#000080",r.center,max(2,r.h//7),1)
    elif country=="Pakistan":
        pygame.draw.rect(surface,"#01411C",r); pygame.draw.rect(surface,"white",(r.x,r.y,r.w//4,r.h)); pygame.draw.circle(surface,"white",r.center,r.h//4); pygame.draw.circle(surface,"#01411C",(r.centerx+r.h//10,r.centery-r.h//12),r.h//4)
    elif country in {"England"}:
        pygame.draw.rect(surface,"white",r); pygame.draw.rect(surface,"#CE1124",(r.x,r.centery-r.h//9,r.w,max(2,r.h//5))); pygame.draw.rect(surface,"#CE1124",(r.centerx-r.w//14,r.y,max(2,r.w//7),r.h))
    elif country=="Bangladesh":
        pygame.draw.rect(surface,"#006A4E",r); pygame.draw.circle(surface,"#F42A41",(r.centerx-r.w//12,r.centery),r.h//3)
    elif country=="Sri Lanka":
        pygame.draw.rect(surface,"#8D153A",r); pygame.draw.rect(surface,"#FFB81C",r,2); pygame.draw.rect(surface,"#00534E",(r.x+2,r.y+2,r.w//5,r.h-4)); pygame.draw.rect(surface,"#EB7400",(r.x+2+r.w//5,r.y+2,r.w//5,r.h-4))
    elif country=="South Africa":
        pygame.draw.rect(surface,"#DE3831",r); pygame.draw.polygon(surface,"#007A4D",[(r.x,r.y),(r.centerx,r.centery),(r.x,r.bottom)]); pygame.draw.line(surface,"white",(r.x,r.y+2),(r.centerx,r.centery),2); pygame.draw.line(surface,"#FFB612",(r.x,r.bottom-2),(r.centerx,r.centery),2); pygame.draw.rect(surface,"#002395",(r.centerx,r.y,r.w//2,r.h//2))
    elif country in {"Australia","New Zealand"}:
        pygame.draw.rect(surface,"#012169",r); pygame.draw.line(surface,"white",r.topleft,r.bottomright,2); pygame.draw.line(surface,"white",r.topright,r.bottomleft,2); pygame.draw.circle(surface,"#E4002B",(r.right-r.w//5,r.centery),max(2,r.h//7))
    elif country=="West Indies":
        pygame.draw.rect(surface,"#7B0041",r); pygame.draw.circle(surface,"#FFD100",r.center,r.h//4); pygame.draw.line(surface,"#007A3D",(r.centerx,r.centery-r.h//4),(r.centerx,r.bottom-2),2)
    else:
        colours={"Afghanistan":("#000000","#D32011","#007A36"),"Ireland":("#169B62","white","#FF883E")}.get(country,("#304FFE","white","#D29922"))
        for i,c in enumerate(colours): pygame.draw.rect(surface,c,(r.x+i*r.w//3,r.y,r.w//3+1,r.h))
    pygame.draw.rect(surface,"#404855",r,1,border_radius=2)
