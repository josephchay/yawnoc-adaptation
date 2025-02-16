import pygame

from . import pygpen as pp


class Minimap(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        self.minimap = self.e['Machines'].minimap.copy()

        self.ui_size = (52, 53)

    def update(self):
        self.minimap = self.e['Machines'].minimap.copy()
        player_pos = (int(self.e['Game'].player.pos[0] // self.e['Tilemap'].tile_size),
                      int(self.e['Game'].player.pos[1] // self.e['Tilemap'].tile_size))
        self.minimap.set_at(player_pos, (131, 206, 62))
        if 'frenemies' in self.e['EntityGroups'].groups:
            for frenemy in self.e['EntityGroups'].groups['frenemies']:
                frenemy_pos = (frenemy.pos[0] // self.e['Tilemap'].tile_size, frenemy.pos[1] // self.e['Tilemap'].tile_size)
                if frenemy.friendly:
                    self.minimap.set_at(frenemy_pos, (131, 206, 62))
                else:
                    self.minimap.set_at(frenemy_pos, (254, 252, 211))

    def render(self):
        map_offset = [self.e['Game'].player.pos[0] / self.e['Tilemap'].tile_size - 26, self.e['Game'].player.pos[1] / self.e['Tilemap'].tile_size - 26]
        map_offset[0] = max(0, min(self.minimap.get_width() - self.ui_size[0], map_offset[0]))
        map_offset[1] = max(0, min(self.minimap.get_height() - self.ui_size[1], map_offset[1]))

        map_subsurf = pp.utils.gfx.clip(self.minimap, pygame.Rect(*map_offset, self.ui_size[0], self.ui_size[1])).convert_alpha()
        map_subsurf.set_alpha(200)

        self.e['Renderer'].blit(map_subsurf, (self.e['Game'].display.get_width() - map_subsurf.get_width() - 4 + self.e['State'].right_inv_offset, 4), z=9997, group='ui')
        self.e['Renderer'].blit(self.e['Assets'].images['misc']['minimap_frame'], (self.e['Game'].display.get_width() - map_subsurf.get_width() - 6 + self.e['State'].right_inv_offset, 2), z=9998, group='ui')