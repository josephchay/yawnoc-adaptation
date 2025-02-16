import random

import pygame
import astar

from . import pygpen as pp
from .pygpen import ElementSingleton, utils, data_structures

from .particle_spawners import update_spawner

from .npc import NPC

TILES_AROUND = [(0, 0), (1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1), (0, 1), (1, 1), (-1, 1)]
TILE_N4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
TILE_N8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]

AUTOTILE_CONFIG = {
    (True, True, True, False): (1, 0),
    (True, True, False, True): (1, 2),
    (True, False, True, True): (0, 1),
    (False, True, True, True): (2, 1),
    (True, False, True, False): (0, 0),
    (False, True, True, False): (2, 0),
    (False, True, False, True): (2, 2),
    (True, False, False, True): (0, 2),
    (True, True, True, True): (1, 1)
}

N8_AUTOTILE_CONFIG = {
    (True, True, True, True, False, True, True, True): (1, 5),
    (True, True, True, True, True, False, True, True): (0, 5),
    (True, True, True, True, True, True, False, True): (1, 4),
    (True, True, True, True, True, True, True, False): (0, 4),
}

AUTOTILE_GROUPS = {'grass', 'floorgrass', 'floorgrassdark'}
RANDOMIZE_GROUPS = {'dirtvariants': (0.5, 4)}
ENTITY_MAP = {(0, 0): (NPC, 'gary')}
PARTICLE_MAP = {(0, 0): 'fire', (1, 0): 'smoke'}

DECOR = {
    'summer': ['bush', 'stone', 'bush', 'stone', 'bush', 'stone', 'red_mushrooms'],
    'fall': ['leaves', 'stone', 'leaves', 'stone', 'leaves', 'stone', 'green_mushrooms'],
    'winter': ['stone', 'stone', 'stone', 'stone', 'brown_mushrooms'],
}
DECOR_SOURCES = {'dirtvariants'}

MAP_NAMES = {
    'summer': ['fortress', 'corners', 'quads', 'river'],
    'fall': ['fall_1'],
}

SHADOW_CACHE = {}

class Pathfind(astar.AStar):
    def __init__(self, tilemap):
        self.tilemap = tilemap

    def neighbors(self, node):
        neighbors = []
        for offset in TILE_N4:
            loc = (node[0] + offset[0], node[1] + offset[1])
            if (loc not in self.tilemap.solids) and (loc not in self.tilemap.gaps):
                neighbors.append(loc)
        return neighbors

    def distance_between(self, node_1, node_2):
        return 1
    
    def heuristic_cost_estimate(self, current, goal):
        return abs(current[0] - goal[0]) + abs(current[1] - goal[1])
    
    def is_goal_reached(self, current, goal):
        return current == goal

class ShadowTile:
    def __init__(self, parent, img, pos):
        self.parent = parent
        self.pos = pos
        self.img = img

    def render(self, offset):
        rpos = (self.pos[0] * self.parent.tile_size - offset[0], self.pos[1] * self.parent.tile_size - offset[1])

        z = -5.5

        if not self.parent.e['Machines'].high_life:
            self.parent.e['Renderer'].blit(self.img, rpos, z=z)

class Decor:
    def __init__(self, parent, category, subtype, rect):
        self.parent = parent
        self.category = category
        self.subtype = subtype
        self.rect = rect

        self.opacity = 255

    @property
    def e(self):
        return self.parent.e

    def render(self):
        if self.category == 'floor_decor':
            img = self.e['Assets'].spritesheets['decor']['assets'][self.subtype]
            self.e['Renderer'].blit(img, (self.rect.x - self.e['Game'].camera[0], self.rect.y - self.e['Game'].camera[1]), z=-99998.5)
        if self.category == 'wall_decor':
            img = self.e['Assets'].spritesheets['decor']['assets'][self.subtype]
            self.e['Renderer'].blit(img, (self.rect.x - self.e['Game'].camera[0], self.rect.y - self.e['Game'].camera[1]), z=self.rect.bottom / self.parent.tile_size - 0.5)
        if self.category == 'tree_decor':
            img = self.e['Assets'].spritesheets['decor']['assets'][self.subtype]
            self.e['Renderer'].blit(img, (self.rect.x - self.e['Game'].camera[0], self.rect.y - self.e['Game'].camera[1]), z=5990 + self.rect.bottom / self.parent.tile_size)
        if self.category == 'ground_decor':
            img = self.e['Assets'].images['decor'][self.subtype]
            shadow_img = self.e['Assets'].images['misc']['shadow_medium']
            self.e['Renderer'].blit(img, (self.rect.x - self.e['Game'].camera[0], self.rect.y - self.e['Game'].camera[1]), z=self.rect.bottom / self.parent.tile_size - 0.5)
            self.e['Renderer'].blit(shadow_img, (self.rect.x - self.e['Game'].camera[0] + (img.get_width() - shadow_img.get_width()) // 2 + 1, self.rect.y - self.e['Game'].camera[1] + img.get_height() - shadow_img.get_height() // 2 - 2), z=-99998)
        if self.category[:7] == 'foliage':
            tree_anim = self.e['Assets'].foliage.foliage[self.category][self.subtype]
            self.opacity = min(255, self.opacity + self.e['Window'].dt * 500)
            if self.rect.colliderect(self.e['Game'].player.rect):
                self.opacity = max(25, self.opacity - self.e['Window'].dt * 2000)
            growth = 8
            tree_surf = tree_anim.prerender(m_clock=self.e['Window'].time, seed=self.rect.x + self.rect.y, opacity=self.opacity, growth=growth)
            self.e['Renderer'].blit(tree_surf, (self.rect.x - self.e['Game'].camera[0] - growth, self.rect.y - self.e['Game'].camera[1] - growth), z=5990 + self.rect.bottom / self.parent.tile_size)
            # used for showing hidden machines later
            self.e['HUD'].coverage_mask_src.blit(tree_surf, (self.rect.x - self.e['Game'].camera[0] - growth, self.rect.y - self.e['Game'].camera[1] - growth))

class Tile:
    def __init__(self, parent, tile_type, pos, wall=False, variant=None, z_offset=0, overhang=False):
        self.pos = pos
        self.parent = parent
        self.type = tile_type
        self.wall = wall
        self.z_offset = z_offset
        self.overhang = overhang

        self.variant = variant

        if self.type in RANDOMIZE_GROUPS:
            if random.random() < RANDOMIZE_GROUPS[self.type][0]:
                self.variant = (random.randint(0, RANDOMIZE_GROUPS[self.type][1] - 1), self.variant[1] if self.variant[1] else 0)

    @property
    def rect(self):
        return pygame.Rect(self.pos[0] * self.parent.tile_size, self.pos[1] * self.parent.tile_size, self.parent.tile_size, self.parent.tile_size)

    def render(self, offset):
        rpos = (self.pos[0] * self.parent.tile_size - offset[0], self.pos[1] * self.parent.tile_size - offset[1])

        z = -99999
        if self.wall:
            z = self.pos[1] + 1
        z += self.z_offset

        if self.parent.e['Machines'].high_life:
            z = -10
            if self.pos in self.parent.solids:
                img = self.parent.e['Assets'].images['tiles']['hl_wall']
            elif self.pos not in self.parent.gaps:
                img = self.parent.e['Assets'].images['tiles']['hl_square']
            else:
                img = self.parent.e['Assets'].images['tiles']['hl_gap']
            timer = max(0, self.parent.e['Machines'].high_life_time - 1.5)
            draw_number = True
            if 0 < timer < 2.5:
                dis = utils.game_math.distance(self.parent.e['HighlifeMap'].center, (self.pos[0] * self.parent.tile_size, self.pos[1] * self.parent.tile_size))
                if dis > (max(self.parent.dimensions) * 1.5 * self.parent.tile_size + 24) * timer:
                    img = self.parent.e['Assets'].images['tiles']['hl_none']
                draw_number = False
                if timer > 1:
                    if dis < (max(self.parent.dimensions) * 1.5 * self.parent.tile_size + 24) * (timer * 0.5 - 0.5):
                        draw_number = True
            if not timer:
                img = self.parent.e['Assets'].images['tiles']['hl_none']
                draw_number = False
            if draw_number and (not any([pos in self.parent.solids for pos in [self.pos, (self.pos[0] - 1, self.pos[1]), (self.pos[0], self.pos[1] - 1)]])):
                if self.pos[1] == self.parent.dimensions[1] // 2:
                    number = self.pos[0] - self.parent.dimensions[0] // 2
                    if number % 2 == 1:
                        number = str(number)
                        self.parent.e['Text']['small_font'].renderzb(number, (rpos[0] - 1 - self.parent.e['Text']['small_font'].width(number) / 2, rpos[1] + 3), color=(100, 97, 139), bgcolor=(38, 27, 46), group='default', z=z + 0.1)
                if self.pos[0] == self.parent.dimensions[0] // 2:
                    number = -(self.pos[1] - self.parent.dimensions[1] // 2)
                    if number % 2 == 1:
                        number = str(number)
                        self.parent.e['Text']['small_font'].renderzb(number, (rpos[0] - 5 - self.parent.e['Text']['small_font'].width(number) / 2, rpos[1] - 3), color=(100, 97, 139), bgcolor=(38, 27, 46), group='default', z=z + 0.1)
        else:
            if self.variant:
                img = self.parent.e['Assets'].spritesheets[self.type]['assets'][self.variant]
            else:
                img = self.parent.e['Assets'].images['tiles'][self.type]
            
            if self.overhang:
                self.parent.e['HUD'].coverage_mask_src.blit(img, rpos)
        self.parent.e['Renderer'].blit(img, rpos, z=z)

class Tilemap(ElementSingleton):
    def __init__(self):
        super().__init__()

        self.tile_size = 12
        self.wall_height = 12
        self.dimensions = (64, 64)

        self.pathfinder = Pathfind(self)

        self.load_map('fortress')

    def load_random_map(self):
        try:
            map_choice = random.choice(MAP_NAMES[self.e['State'].season])
            self.load_map(map_choice)
            return map_choice
        except FileNotFoundError:
            self.e['Game'].restart()

    def clear(self):
        self.floor = {}
        self.walls = {}
        self.solids = {}
        self.gaps = {}
        self.shadows = {}
        self.decor_block = {}
        self.particle_spawners = []
        self.decor_quads = data_structures.Quads(self.tile_size * 3)

        self.spawn = (300, 300)
        self.respawn = (300, 300)
        self.exit = (300, 350)
        self.shops = []
        self.weapon_shops = []

        self.e['Game'].gm.clear()

        if 'entities' in self.e['EntityGroups'].groups:
            for entity in list(self.e['EntityGroups'].groups['entities']):
                if type(entity).__name__ == 'TempTerrain':
                    self.e['EntityGroups'].groups['entities'].remove(entity)
        
        if 'particles' in self.e['EntityGroups'].groups:
            del self.e['EntityGroups'].groups['particles']

    def load_map(self, map_name):
        self.clear()

        map_data = utils.io.read_tjson(f'data/maps/{map_name}.pmap')

        self.dimensions = map_data['dimensions']
        self.minimap_base = pygame.Surface(self.e['Tilemap'].dimensions)

        self.wall_map = pygame.Surface(self.dimensions, pygame.SRCALPHA)

        for obj_id in map_data['offgrid_tiles']['objects']:
            tile = map_data['offgrid_tiles']['objects'][obj_id]
            tile_id = tuple(tile['tile_id'])
            img = self.e['Assets'].spritesheets[tile['group']]['assets'][tile_id]
            group_conf = self.e['Assets'].spritesheets[tile['group']]['config']
            tile_conf = {}
            if tile_id in group_conf:
                tile_conf = group_conf[tile_id]

            categories = []
            if 'categories' in tile_conf:
                categories = tile_conf['categories']

            if tile['group'] in {'foliage', 'foliagefall', 'foliagewinter'}:
                decor = Decor(self, tile['group'], tile_id, pygame.Rect(tile['pos'][0], tile['pos'][1], *img.get_size()))
                self.decor_quads.add_raw(decor, decor.rect, tag=True)
            
            if tile['group'] == 'entities':
                if tile_id in ENTITY_MAP:
                    entity = ENTITY_MAP[tile_id][0](ENTITY_MAP[tile_id][1], tile['pos'])
                    self.e['EntityGroups'].add(entity, 'entities')
            
            if tile['group'] == 'particles':
                self.particle_spawners.append((PARTICLE_MAP[tile_id], tile['pos']))
            
            if 'wall_decor' in categories:
                decor = Decor(self, 'wall_decor', tile_id, pygame.Rect(tile['pos'][0], tile['pos'][1], *img.get_size()))
                self.decor_quads.add_raw(decor, decor.rect, tag=True)
            if 'tree_decor' in categories:
                decor = Decor(self, 'tree_decor', tile_id, pygame.Rect(tile['pos'][0], tile['pos'][1], *img.get_size()))
                self.decor_quads.add_raw(decor, decor.rect, tag=True)
            if 'floor_decor' in categories:
                decor = Decor(self, 'floor_decor', tile_id, pygame.Rect(tile['pos'][0], tile['pos'][1], *img.get_size()))
                self.decor_quads.add_raw(decor, decor.rect, tag=True)

        for loc in map_data['grid_tiles']:
            tile_stack = map_data['grid_tiles'][loc]
            for layer in tile_stack:
                tile = tile_stack[layer]
                group_conf = self.e['Assets'].spritesheets[tile['group']]['config']
                tile_id = tuple(tile['tile_id'])
                if tile_id in group_conf:
                    tile_conf = group_conf[tile_id]
                    categories = ['floor']
                    if 'categories' in tile_conf:
                        categories = tile_conf['categories']
                    if 'solid' in categories:
                        self.solids[loc] = Tile(self, tile['group'], loc, variant=tile_id)
                    if 'floor' in categories:
                        # don't overwrite 'backwall' tiles
                        if (loc not in self.floor) and (loc not in self.walls):
                            self.floor[loc] = Tile(self, tile['group'], loc, variant=tile_id)
                    if 'backwall' in categories:
                        self.floor[loc] = Tile(self, tile['group'], loc, variant=tile_id)
                        self.solids[loc] = self.floor[loc]
                        self.minimap_base.set_at(loc, (67, 51, 87))
                    if 'wall' in categories:
                        self.walls[loc] = Tile(self, tile['group'], loc, variant=tile_id, wall=True)
                        self.solids[loc] = self.walls[loc]
                        self.minimap_base.set_at(loc, (67, 51, 87))
                    if 'overhang' in categories:
                        self.walls[loc] = Tile(self, tile['group'], loc, variant=tile_id, wall=True, overhang=True)
                    if 'cliff' in categories:
                        self.floor[loc] = Tile(self, tile['group'], loc, variant=tile_id)
                        self.gaps[loc] = self.floor[loc]
                        self.minimap_base.set_at(loc, (74, 156, 223))
                    if 'grass' in categories:
                        if tile_id == (0, 2):
                            self.e['Game'].gm.place_tile(loc, random.randint(8, 10), [0, 1, 2, 3, 4, 5, 6])
                        elif tile_id == (1, 2):
                            self.e['Game'].gm.place_tile(loc, random.randint(3, 5), [0, 1, 2, 3, 6])
                        if tile_id == (2, 2):
                            self.e['Game'].gm.place_tile(loc, random.randint(8, 10), [7, 8])
                        elif tile_id == (3, 2):
                            self.e['Game'].gm.place_tile(loc, random.randint(3, 5), [7, 8])
                        if tile_id == (4, 2):
                            self.e['Game'].gm.place_tile(loc, random.randint(8, 10), [9, 10, 11, 12])
                        elif tile_id == (5, 2):
                            self.e['Game'].gm.place_tile(loc, random.randint(3, 5), [9, 10, 11, 12])
                    if 'spawn' in categories:
                        self.spawn = (tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size)
                    if 'respawn' in categories:
                        self.respawn = (tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size)
                    if 'exit' in categories:
                        self.exit = (tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size)
                    if 'shop' in categories:
                        self.shops.append((tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size))
                    if 'weapon' in categories:
                        self.weapon_shops.append((tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size))
                    if 'block_decor' in categories:
                        self.decor_block[loc] = True
        
        # fill in places with no tiles using gaps for water
        for x in range(self.dimensions[0]):
            for y in range(self.dimensions[1]):
                if not any([(x, y) in section for section in [self.walls, self.solids, self.floor, self.gaps]]):
                    self.gaps[(x, y)] = Tile(self, 'water_wall', (x, y))
                    self.minimap_base.set_at((x, y), (74, 156, 223))

                if ((x, y) in self.floor) and ((x, y) not in self.solids) and ((x, y) not in self.decor_block):
                    tile = self.floor[(x, y)]
                    neighbors = []
                    for offset in TILE_N4:
                        loc = (x + offset[0], y + offset[1])
                        neighbors.append((loc in self.floor) and (loc not in self.solids) and (self.floor[loc].type in DECOR_SOURCES))
                    if tile.type in DECOR_SOURCES:
                        for i in range(4):
                            if random.random() < 0.006 * len(DECOR[self.e['State'].season]):
                                decor_type = random.choice(DECOR[self.e['State'].season])
                                img = self.e['Assets'].images['decor'][decor_type]
                                offset = (random.random() * self.tile_size, random.random() * self.tile_size)
                                rect = pygame.Rect(x * self.tile_size + offset[0] - img.get_width() // 2, y * self.tile_size + offset[1] - img.get_height() // 2, *img.get_size())
                                if (not neighbors[0]) and (rect.right >= (x + 1) * self.tile_size):
                                    continue
                                if (not neighbors[1]) and (rect.left < x * self.tile_size):
                                    continue
                                if (not neighbors[2]) and (rect.bottom >= (y + 1) * self.tile_size):
                                    continue
                                if (not neighbors[3]) and (rect.top < y * self.tile_size):
                                    continue
                                decor = Decor(self, 'ground_decor', decor_type, rect)
                                self.decor_quads.add_raw(decor, decor.rect, tag=True)
        
        # generate wall map
        for x in range(self.dimensions[0]):
            for y in range(self.dimensions[1]):
                if not self.is_open_space((x, y)):
                    self.wall_map.set_at((x, y), (0, 0, 255, 255))

        self.generate_shadows()

    def closest_space(self, pos):
        loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size))
        if self.is_open_space(loc):
            return loc
        checked = []
        neighbors = [loc]
        while True:
            old_neighbors = neighbors.copy()
            neighbors = []
            for neighbor in old_neighbors:
                for offset in TILE_N4:
                    loc = (neighbor[0] + offset[0], neighbor[1] + offset[1])
                    if loc not in checked:
                        if self.is_open_space(loc):
                            return loc
                        neighbors.append(loc)
                checked.append(neighbor)
    
    def is_open_space(self, loc):
        if (loc not in self.solids) and (loc not in self.gaps):
            return True
        return False

    def visible_solid(self, loc):
        if loc in self.solids:
            return (self.solids[loc].type, self.solids[loc].variant) != ('special', (3, 3))

    def generate_shadows(self):
        for y in range(self.dimensions[0]):
            for x in range(self.dimensions[1]):
                if self.visible_solid((x, y)) or ((x, y) in self.walls):
                    continue

                neighbors = set()
                for offset in TILE_N8:
                    loc = (x + offset[0], y + offset[1])
                    if self.visible_solid(loc):
                        neighbors.add(offset)

                tile_images = [None] * 4

                # top-left corner
                if ((-1, 0) in neighbors) and ((0, -1) in neighbors):
                    tile_images[0] = (0, 0)
                elif ((-1, -1) in neighbors) and ((0, -1) in neighbors):
                    tile_images[0] = (0, 2)
                elif ((-1, 0) in neighbors) and ((-1, -1) in neighbors):
                    tile_images[0] = (0, 1)

                # top-right corner
                if ((1, 0) in neighbors) and ((0, -1) in neighbors):
                    tile_images[1] = (1, 0)
                elif ((1, -1) in neighbors) and ((0, -1) in neighbors):
                    tile_images[1] = (1, 1)
                elif ((1, 0) in neighbors) and ((1, -1) in neighbors):
                    tile_images[1] = (1, 2)
                
                # bottom-right corner
                if ((1, 0) in neighbors) and ((0, 1) in neighbors):
                    tile_images[2] = (2, 0)
                elif ((1, 1) in neighbors) and ((0, 1) in neighbors):
                    tile_images[2] = (2, 2)
                elif ((1, 0) in neighbors) and ((1, 1) in neighbors):
                    tile_images[2] = (2, 1)

                # bottom-left corner
                if ((-1, 0) in neighbors) and ((0, 1) in neighbors):
                    tile_images[3] = (3, 0)
                elif ((-1, 1) in neighbors) and ((0, 1) in neighbors):
                    tile_images[3] = (3, 1)
                elif ((-1, 0) in neighbors) and ((-1, 1) in neighbors):
                    tile_images[3] = (3, 2)

                shadow_id = tuple(tile_images)
                if any(shadow_id):
                    if shadow_id not in SHADOW_CACHE:
                        shadow_img = pygame.Surface((self.tile_size, self.tile_size))
                        shadow_img.set_colorkey((0, 0, 0))
                        if tile_images[0]:
                            shadow_img.blit(self.e['Assets'].spritesheets['shadows']['assets'][tile_images[0]], (0, 0))
                        if tile_images[1]:
                            shadow_img.blit(self.e['Assets'].spritesheets['shadows']['assets'][tile_images[1]], (0, 0))
                        if tile_images[2]:
                            shadow_img.blit(self.e['Assets'].spritesheets['shadows']['assets'][tile_images[2]], (0, 0))
                        if tile_images[3]:
                            shadow_img.blit(self.e['Assets'].spritesheets['shadows']['assets'][tile_images[3]], (0, 0))
                        shadow_img.set_alpha(130)
                        SHADOW_CACHE[shadow_id] = shadow_img
                    shadow_img = SHADOW_CACHE[shadow_id]
                    self.shadows[(x, y)] = ShadowTile(self, shadow_img, (x, y))

    def physics_gridline(self, start, end, include_gaps=True):
        for loc in pp.utils.game_math.grid_line(start, end):
            if loc in self.solids:
                return True
            elif include_gaps and (loc in self.gaps):
                return True
        return False

    def solid_check(self, pos_px, include_gaps=True):
        loc = (int(pos_px[0] // self.tile_size), int(pos_px[1] // self.tile_size))
        if loc in self.solids:
            return True
        elif include_gaps and (loc in self.gaps):
            return True
        return False

    def solids_around(self, pos_px, include_gaps=True):
        pos = (int(pos_px[0] // self.tile_size), int(pos_px[1] // self.tile_size))
        solids = []
        for offset in TILES_AROUND:
            check = (pos[0] + offset[0], pos[1] + offset[1])
            if check in self.solids:
                solids.append(self.solids[check])
            elif include_gaps and (check in self.gaps):
                solids.append(self.gaps[check])
        return solids
    
    def update(self):
        for spawner in self.particle_spawners:
            update_spawner(*spawner, self)

    def render(self):
        cam_r = self.e['Game'].camera.rect
        tl = (cam_r.left // self.tile_size, cam_r.top // self.tile_size - 1)
        br = (cam_r.right // self.tile_size, cam_r.bottom // self.tile_size)
        for y in range(tl[1], br[1] + 2):
            for x in range(tl[0], br[0] + 1):
                if (x, y) in self.floor:
                    self.floor[(x, y)].render(cam_r.topleft)
                if (x, y) in self.shadows:
                    self.shadows[(x, y)].render(cam_r.topleft)
                if (x, y) in self.walls:
                    self.walls[(x, y)].render(cam_r.topleft)
                if self.e['Machines'].high_life and ((x, y) in self.gaps):
                    self.gaps[(x, y)].render(cam_r.topleft)
        
        if not self.e['Machines'].high_life:
            for decor in self.decor_quads.query(cam_r):
                decor.render()