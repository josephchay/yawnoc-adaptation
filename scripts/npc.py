import math
import random

import pygame

from .pygpen import Entity
from .pygpen.utils.game_math import distance

DIALOGUE = {
    'gary': ['A fine weapon you have, but they can always be improved!']
}

INWORLD_DIALOGUE = {
    'gary': ['Welcome back!', 'How goes the fight?']
}

NAMES = {
    'gary': 'Gary'
}

class NPC(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.type == 'gary':
            self.z = (self.pos[1] + 47.01) / self.e['Tilemap'].tile_size
        else:
            # todo: add height offset similar to player
            self.z = self.pos[1] / self.e['Tilemap'].tile_size

        self.name = 'unknown'
        if self.type in NAMES:
            self.name = NAMES[self.type]

        self.spoken = False
        self.speech_bubble = [None, 0, False]

    @property
    def head_origin(self):
        origin = self.pos

        if self.type == 'gary':
            origin = (self.pos[0] + 31, self.pos[1] + 19)

        return origin

    @property
    def hitbox_origin(self):
        origin = self.pos

        if self.type == 'gary':
            origin = (self.pos[0] + 30, self.pos[1] + 38)

        return origin

    def interact(self):
        if self.type in DIALOGUE:
            self.e['State'].dialogue = [self, DIALOGUE[self.type].copy()]

    def update(self, dt):
        super().update(dt)

        player_distance = distance(self.e['Game'].player.pos[:2], self.hitbox_origin)
        if player_distance < 14:
            if self.e['State'].closest_entity[1] > player_distance:
                self.e['State'].closest_entity = [self, player_distance]
        
        if self.type in INWORLD_DIALOGUE:
            if player_distance < 140:
                if not self.spoken:
                    self.spoken = True
                    self.speech_bubble = [random.choice(INWORLD_DIALOGUE[self.type]), 0, False]

    def renderz(self, offset=(0, 0), group='default'):
        super().renderz(offset=offset, group=group)

        if self.type == 'gary':
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['gary_tail'], self.topleft(offset), z=-99997, group=group)

        if self.speech_bubble[0]:
            if self.speech_bubble[2]:
                self.speech_bubble[1] = max(0, min(len(self.speech_bubble[0]) / 25 + 1 / 6, self.speech_bubble[1] - self.e['Window'].dt * 5))
                if not self.speech_bubble[1]:
                    self.speech_bubble = [None, 0, False]
            else:
                self.speech_bubble[1] += self.e['Window'].dt
            if self.speech_bubble[0]:
                init_progress = min(self.speech_bubble[1] * 6, 1)
                text_progress = max(0, self.speech_bubble[1] - 1 / 6)
                chars_to_show = int(text_progress * 25)
                finished_for = text_progress - (len(self.speech_bubble[0]) / 25)
                if finished_for > 4:
                    self.speech_bubble[2] = True
                text = self.speech_bubble[0][:chars_to_show]
                text_width = self.e['Text']['small_font'].width(text)
                src = (self.head_origin[0] + 7, self.head_origin[1] - 7)
                polygon_points = [
                    (6 * init_progress, -4 * init_progress),
                    (0, 0),
                    (5 * init_progress, -6 * init_progress),
                    (4 * init_progress, -9 * init_progress),
                    (6 * init_progress, -14 * init_progress),
                    (8 * init_progress + text_width * 0.5, -15 * init_progress),
                    (10 * init_progress + text_width, -14 * init_progress),
                    (12 * init_progress + text_width, -9 * init_progress),
                    (10 * init_progress + text_width, -4 * init_progress),
                    (8 * init_progress + text_width * 0.5, -3 * init_progress),
                    (6 * init_progress, -4 * init_progress),
                ]
                t = self.e['Window'].time
                polygon_points = [(p[0] + math.sin(i + t * 1.5) * 1.5, p[1] + math.cos(i + t * 1.2) * 1.5) for i, p in enumerate(polygon_points)]
                bubble_surf = pygame.Surface((text_width + 20, 20), pygame.SRCALPHA)
                pygame.draw.polygon(bubble_surf, (38, 27, 46), [(p[0], p[1] + bubble_surf.get_height()) for p in polygon_points])
                self.e['Text']['small_font'].renderz(text, (src[0] - self.e['Game'].camera[0] + 8, src[1] - self.e['Game'].camera[1] - 12), color=(254, 252, 211), z=101, group='ui')
                bubble_surf.set_alpha(150)
                self.e['Renderer'].blit(bubble_surf, (src[0] - self.e['Game'].camera[0], src[1] - self.e['Game'].camera[1] - bubble_surf.get_height()), z=100, group='ui')