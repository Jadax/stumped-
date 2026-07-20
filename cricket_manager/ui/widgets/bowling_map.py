"""Professional bowling line-and-length heat map."""
from __future__ import annotations
import pygame
from .common import GOLD,GREEN,RED,MUTED,text
class BowlingMap:
 def __init__(self,rect,events):self.rect=pygame.Rect(rect);self.events=events
 def draw(self,surface):
  s=3;cv=pygame.Surface((self.rect.w*s,self.rect.h*s));cv.fill("#ad9163");w,h=cv.get_size()
  for fraction,label in ((.25,"SHORT"),(.5,"GOOD"),(.72,"FULL"),(.88,"YORKER")):
   y=int(h*fraction);pygame.draw.line(cv,"#e1d4b8",(0,y),(w,y),3)
  pygame.draw.line(cv,"#f0f6fc",(w//3,0),(w//3,h),2);pygame.draw.line(cv,"#f0f6fc",(w*2//3,0),(w*2//3,h),2)
  for e in self.events:
   x=int(float(e.get("x",.5))*w);y=int(float(e.get("y",.5))*h);col=RED if e.get("wicket") else GOLD if e.get("runs",0)>=4 else GREEN
   pygame.draw.circle(cv,col,(x,y),10 if e.get("wicket") else 6)
  surface.blit(pygame.transform.smoothscale(cv,self.rect.size),self.rect);text(surface,"Leg  •  Middle  •  Off",(self.rect.centerx,self.rect.bottom+4),10,MUTED,anchor="midtop")
