"""Compact custom international tournament builder."""
from __future__ import annotations
import pygame
from ui.shared_components import BaseScreen
from ui.widgets import Button, ButtonStyle, Card
from ui.widgets.common import BG, GOLD, GREEN, MUTED, RED, WHITE, text


class TournamentSetupScreen(BaseScreen):
    title = "Tournament Setup"
    def build(self) -> None:
        self.nations = self.context["game_controller"].countries
        self.selected = {country["id"] for country in self.nations[:8]}
        self.format = "T20"; self.message = ""
        r=self.content_rect; self.card=Card(pygame.Rect(r.x+32,r.y+104,r.width-64,r.height-182),"Custom Championship","SELECT 4–12 TEAMS")
        self.buttons={}; cols=4; gap=10; bw=(self.card.content_rect.width-gap*3)//4
        for i,country in enumerate(self.nations):
            rect=pygame.Rect(self.card.content_rect.x+(i%cols)*(bw+gap),self.card.content_rect.y+(i//cols)*47,bw,37)
            self.buttons[country["id"]]=Button(rect,f"{country['flag']} {country['name']}",ButtonStyle.PRIMARY if i<8 else ButtonStyle.SECONDARY,selected=i<8)
        self.format_button=Button(pygame.Rect(r.centerx-100,r.bottom-58,200,39),"FORMAT: T20",ButtonStyle.PRIMARY)
        self.back_button=Button(pygame.Rect(r.x+32,r.bottom-58,140,39),"BACK",ButtonStyle.SECONDARY)
        self.confirm_button=Button(pygame.Rect(r.right-252,r.bottom-58,220,39),"CREATE TOURNAMENT",ButtonStyle.SUCCESS)
    def process_event(self,event:pygame.event.Event)->None:
        if self.back_button.process_event(event): self.navigate("New Game Setup"); return
        if self.format_button.process_event(event):
            formats=["T10","T20","Hundred","ODI","Test"]; self.format=formats[(formats.index(self.format)+1)%len(formats)]; self.format_button.label=f"FORMAT: {self.format.upper()}"
        for country_id,button in self.buttons.items():
            if button.process_event(event):
                if country_id in self.selected: self.selected.remove(country_id)
                elif len(self.selected)<12: self.selected.add(country_id)
                button.selected=country_id in self.selected; button.style=ButtonStyle.PRIMARY if button.selected else ButtonStyle.SECONDARY
        if self.confirm_button.process_event(event):
            try: self.context["game_controller"].confirm_custom_tournament(sorted(self.selected),self.format)
            except ValueError as exc: self.message=str(exc)
    def draw(self,surface:pygame.Surface)->None:
        pygame.draw.rect(surface,BG,self.content_rect); text(surface,"BUILD A TOURNAMENT",(self.content_rect.x+34,self.content_rect.y+24),30,WHITE,True)
        text(surface,"Choose the nations and format. A balanced round-robin schedule is generated automatically.",(self.content_rect.x+35,self.content_rect.y+65),15,MUTED)
        self.card.draw(surface)
        for button in self.buttons.values(): button.draw(surface)
        text(surface,f"{len(self.selected)} TEAMS SELECTED",(self.card.rect.right-18,self.card.rect.bottom-26),12,GOLD,True,anchor="topright")
        self.back_button.draw(surface); self.format_button.draw(surface); self.confirm_button.draw(surface)
        if self.message:text(surface,self.message,(self.content_rect.centerx,self.content_rect.bottom-75),12,RED,True,anchor="center")
