import math
import random

import pygame

from . import pygpen as pp

from .tilemap import Tile

class TempTerrain(pp.Element):
    def __init__(self, terrain_type, pos):
        super().__init__()

        self.type = terrain_type
        self.pos = tuple(pos)
        self.px_pos = ((self.pos[0] + 0.5) * self.e['Tilemap'].tile_size, (self.pos[1] + 0.5) * self.e['Tilemap'].tile_size)
    
        self.tile = Tile(self.e['Tilemap'], 'tempterrain', self.pos, wall=True, variant=self.type, z_offset=-1)

        self.rect = pygame.Rect(self.pos[0] * self.e['Tilemap'].tile_size, self.pos[1] * self.e['Tilemap'].tile_size, self.e['Tilemap'].tile_size, self.e['Tilemap'].tile_size)
        if (not self.rect.colliderect(self.e['Game'].player.rect)) and self.e['Tilemap'].is_open_space(self.pos):
            self.e['Tilemap'].solids[self.pos] = self.tile

            self.poof()

            self.life = 15
        else:
            self.life = 0

        self.y_offset = self.e['Assets'].spritesheets[self.tile.type]['assets'][self.tile.variant].get_height() - self.e['Tilemap'].tile_size

    def poof(self):
        spark_colors = [(193, 159, 113), (149, 86, 68), (106, 51, 60)]
        for i in range(20):
            self.e['EntityGroups'].add(pp.vfx.Spark(self.px_pos, random.random() * math.pi * 2, size=(random.randint(3, 6), random.randint(1, 2)), speed=random.random() * 70 + 70, decay=random.random() * 3 + 0.5, color=random.choice(spark_colors), z=5981), 'vfx')
    
    def update(self, dt):
        self.life -= dt

        if self.life <= 0:
            if self.pos in self.e['Tilemap'].solids:
                self.poof()
                del self.e['Tilemap'].solids[self.pos]
            return True
    
    def renderz(self, offset=(0, 0), group='default'):
        if self.life:
            self.tile.render(offset=(offset[0], offset[1] + self.y_offset))
