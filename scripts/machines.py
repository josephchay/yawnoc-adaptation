import time
import math
import random

import pygame

from . import pygpen as pp

from .bullet import Bullet
from .rig import CentipedeRig
from .drops import Drop
from .debris import Debris, AbilityDrop, Bomb
from .animation import Animation
from .attack_circle import AttackCircle
from .automata import Automata
from .frenemy import Frenemy

MACHINE_TYPES = ['cube', 'cylinder', 'egg', 'crab', 'bishop', 'volcano', 'spawner', 'beacon']
WEIGHTED_MACHINE_TYPES = ['cube', 'cube', 'cylinder', 'egg', 'crab', 'crab', 'bishop', 'volcano', 'spawner', 'beacon']
MACHINE_ID = {machine: i + 100 for i, machine in enumerate(MACHINE_TYPES)}
MACHINE_ID['beacon'] = 255
MACHINE_ID['chest'] = 254
MACHINE_ID['spawner'] = 253
MACHINE_ID['stump'] = 252
INV_MACHINE_ID = {v: k for k, v in MACHINE_ID.items()}

EVENT_NAMES = {
    'summer': 'HighLife',
    'fall': 'Brian\'s Migraine',
    'winter': 'Bruh',
}

MACHINE_OFFSETS = {
    'crab': (0, -3),
    'cube': (0, -5),
    'cylinder': (0, -6),
    'egg': (0, -2),
    'beacon': (0, -4),
    'bishop': (0, -7),
    'volcano': (0, -2),
    'chest': (0, -5),
    'stump': (-1, -3),
    'spawner': (0, -8),
}

PATTERN_DIFFICULTY = {
    'beacon': 2,
    'blinker': 1,
    'tub': 1,
    'glider': 3,
    'lwss': 4,
    'mwss': 5,
    'glider_gun': 10,
    'brain_1': 12,
    'brain_2': 6,
    'brain_3': 2,
}

SEASON_PATTERNS = {
    'summer': ['beacon', 'blinker', 'tub', 'glider', 'lwss', 'mwss', 'glider_gun'],
    'fall': ['brain_1', 'brain_2', 'brain_3'],
    'winter': ['beacon', 'tub', 'blinker'],
}

STABLE_MACHINES = {'beacon', 'chest', 'stump', 'spawner'}

MINOR_PATTERNS = [pattern for pattern in PATTERN_DIFFICULTY if PATTERN_DIFFICULTY[pattern] < 5]

NEIGHBOR_9 = [(0, 0), (1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1), (0, 1), (1, 1), (-1, 1)]
NEIGHBOR_8 = [(1, 0), (-1, 0), (0, -1), (1, -1), (-1, -1), (0, 1), (1, 1), (-1, 1)]

CHEST_REWARDS = ['scrap'] * 3 + ['invincibility', 'collateral', 'lifesteal', 'freeze', 'double_barrel', 'extra_rounds']

class Machine:
    def __init__(self, parent, machine_type, pos, green=255):
        self.parent = parent
        self.type = machine_type
        self.pos = pos

        self.timer = 0
        self.freeze = 0

        self.health = 3
        if self.type == 'egg':
            self.health = 1
        elif self.type == 'beacon':
            self.health = (self.parent.e['State'].wave * 3 + 10) * 3
        elif self.type == 'spawner':
            self.health = 12
        elif self.type == 'stump':
            self.health = 9

        self.max_health = self.health
        self.hurt = 0

        self.alive_for = 0
        if self.pos in self.parent.last_machine_map:
            self.alive_for = 1

        self.size = [0, 0]

        if time.time() - self.parent.wave_start > 2:
            tile_size = self.parent.e['Tilemap'].tile_size
            rect = pygame.Rect(self.pos[0] * tile_size, self.pos[1] * tile_size, tile_size, tile_size)
            if self.parent.e['Game'].player.hitbox.colliderect(rect):
                if self.parent.e['Game'].player.damage(1):
                    self.parent.e['Game'].player.kb_stack.append([math.pi / 2, 100])

        self.parent.minimap.set_at(self.pos, (254, 252, 211))
        if self.type in STABLE_MACHINES:
            if self.type == 'stump':
                self.parent.minimap.set_at(self.pos, (100, 97, 139))
            else:
                self.parent.minimap.set_at(self.pos, (191, 60, 96))

        self.green_stat = green

    def copy(self):
        new_machine = Machine(self.parent, self.type, self.pos, green=self.green_stat)
        new_machine.health = self.health
        new_machine.max_health = self.max_health
        new_machine.freeze = self.freeze
        return new_machine

    def destroy(self):
        if self.pos in self.parent.machine_map:
            del self.parent.machine_map[self.pos]
        self.parent.minimap.set_at(self.pos, (0, 0, 0))
        self.parent.e['State'].score += 11

        if (not len(self.parent.machine_map)) or (self.type == 'beacon'):
            self.parent.e['Game'].freeze_stack.append([0.1, 1])

        for i in range(20):
            self.parent.e['EntityGroups'].add(pp.vfx.Spark(self.center, random.random() * math.pi * 2, size=(random.randint(5, 7), 1), speed=random.random() * 120 + 120, decay=random.random() * 4 + 2, color=random.choice([(254, 252, 211), (38, 27, 46)]), z=0), 'vfx')

        if self.type == 'egg':
            self.parent.e['EntityGroups'].add(CentipedeRig(self.center), 'enemies')
        elif self.type == 'chest':
            for i in range(random.randint(3, 5)):
                self.parent.e['EntityGroups'].add(Debris('plank', self.center), 'vfx')
            reward = random.choice(CHEST_REWARDS)
            if reward == 'scrap':
                for i in range(random.randint(self.parent.e['State'].wave * 2, self.parent.e['State'].wave * 3)):
                    self.parent.e['EntityGroups'].add(Drop('scrap', self.center), 'entities')
            if reward + '_b' in self.parent.e['Assets'].images['upgrades']:
                self.parent.e['EntityGroups'].add(AbilityDrop(reward, self.center), 'entities')
        elif self.type == 'stump':
            for i in range(random.randint(5, 7)):
                self.parent.e['EntityGroups'].add(Debris('plank', self.center), 'vfx')
        else:
            for i in range(random.randint(2, 3)):
                self.parent.e['EntityGroups'].add(Drop('scrap', self.center), 'entities')
            for i in range(random.randint(3, 5)):
                self.parent.e['EntityGroups'].add(Debris(random.choice(['machine_fragment', 'machine_fragment_2', 'machine_fragment_2']), self.center, force=0.35), 'vfx')

        for i in range(random.randint(5, 7)):
            anim = Animation('flash', (self.center[0] + random.randint(-6, 6), self.center[1] + random.randint(-9, 6)))
            anim.animation.update(random.random() * 0.6)
            anim.flip[0] = random.choice([True, False])
            self.parent.e['EntityGroups'].add(anim, 'vfx')

        self.parent.e['Game'].camera.screenshake = max(self.parent.e['Game'].camera.screenshake, 0.15)

        self.parent.e['Game'].player.play_from('destroy', self.center, volume=0.7)

        if self.type == 'beacon':
            self.parent.beacon = None
            anim = Animation('small_explosion', (self.center[0], self.center[1]))
            anim.flip[0] = random.choice([True, False])
            self.parent.e['EntityGroups'].add(anim, 'vfx')

        if self.parent.e['State'].effect_active('collateral'):
            for i in range(random.randint(3, 4)):
                angle = random.random() * math.pi * 2
                self.parent.e['EntityGroups'].add(Bullet('blue', self.center, angle, speed=110), 'entities')

    def damage(self, damage):
        self.parent.e['Game'].player.process_damage_applied(self, damage)
        self.health = max(0, self.health - damage)
        self.hurt = 0.3
        for i in range(random.randint(1, 3)):
            anim = Animation('flash', (self.center[0] + random.randint(-6, 6), self.center[1] + random.randint(-9, 6)))
            anim.animation.update(random.random() * 0.3 + 0.3)
            anim.flip[0] = random.choice([True, False])
            self.parent.e['EntityGroups'].add(anim, 'vfx')
        self.parent.e['Game'].player.play_from('machine_hit', self.center, volume=0.7)
        if not self.health:
            self.destroy()
        elif random.random() < (1 - 0.94 ** self.parent.e['State'].owned_upgrades['frost_touch']):
            self.freeze = 4
            self.parent.e['Game'].player.play_from('freeze', self.center, volume=0.8)

    @property
    def center(self):
        tile_size = self.parent.e['Tilemap'].tile_size
        return ((self.pos[0] + 0.5) * tile_size, (self.pos[1] + 0.5) * tile_size)

    def update(self, activate):
        self.hurt = max(0, self.hurt - self.parent.e['Window'].dt)
        self.alive_for += self.parent.e['Window'].dt
        self.size = [min(1, self.alive_for * 20), min(1, self.alive_for * 30)]
        if not self.freeze:
            self.timer += self.parent.e['Window'].dt
        self.freeze = max(0, self.freeze - self.parent.e['Window'].dt)
        if activate and (not self.parent.e['State'].effect_active('freeze')):
            if self.parent.activation_index == (self.pos[0] + self.pos[1]) % self.parent.activation_groups:
                self.activate()

        if self.type in {'stump', 'chest'}:
            if len(self.parent.machine_map) < 64:
                for machine in list(self.parent.machine_map.values()):
                    if machine.type not in {'stump', 'chest'}:
                        return
                self.damage(self.health)

        if (self.type == 'beacon') and (not (self.parent.e['State'].effect_active('freeze') or self.freeze)):
            if time.time() - self.parent.wave_start > 2:
                if self.timer > 0.2:
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, (time.time() % math.pi) * 2), 'entities')
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, (time.time() % math.pi) * 2 + math.pi), 'entities')
                    self.timer -= 0.2
            else:
                self.timer = 0
        
        if self.parent.e['Settings'].aim_assist:
            player = self.parent.e['Game'].player
            if pp.game_math.fast_range_check(player.center, self.center, player.weapon.max_range):
                angle = math.atan2(self.center[1] - player.center[1], self.center[0] - player.center[0])
                self.parent.machines_in_range.append((angle, len(self.parent.machines_in_range), self))

    def neighbor(self, offset):
        pos = (self.pos[0] + offset[0], self.pos[1] + offset[1])
        if pos in self.parent.machine_map:
            return self.parent.machine_map[pos]
    
    def activate(self):
        if (time.time() - self.parent.wave_start > 2) and (not self.freeze):
            if self.type == 'cube':
                if not self.neighbor((1, 0)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, 0), 'entities')
                if not self.neighbor((-1, 0)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, math.pi), 'entities')
                if not self.neighbor((0, 1)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, math.pi / 2), 'entities')
                if not self.neighbor((0, -1)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, -math.pi / 2), 'entities')
            elif self.type == 'bishop':
                if not self.neighbor((1, 1)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, math.pi / 4), 'entities')
                if not self.neighbor((-1, 1)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, math.pi * 3 / 4), 'entities')
                if not self.neighbor((-1, -1)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, math.pi * 5 / 4), 'entities')
                if not self.neighbor((1, -1)):
                    self.parent.e['EntityGroups'].add(Bullet('red', self.center, math.pi * 7 / 4), 'entities')
            elif self.type == 'volcano':
                offset = ((random.random() - 0.5) * 12 * 6, (random.random() - 0.5) * 12 * 6)
                self.parent.e['EntityGroups'].add(Bomb(self.center, (self.parent.e['Game'].player.center[0] + offset[0], self.parent.e['Game'].player.center[1] + offset[1])), 'entities')
            elif self.type == 'crab':
                angle = math.atan2(self.parent.e['Game'].player.pos[1] - self.center[1], self.parent.e['Game'].player.pos[0] - self.center[0]) + (random.random() * 0.15 - 0.075)
                self.parent.e['EntityGroups'].add(Bullet('red', self.center, angle), 'entities')
            elif self.type == 'cylinder':
                self.parent.e['EntityGroups'].add(AttackCircle((self.center[0], self.center[1] - 5)), 'vfx')
                for i in range(20):
                    self.parent.e['EntityGroups'].add(pp.vfx.Spark(self.center, random.random() * math.pi * 2, size=(random.randint(5, 7), 1), speed=random.random() * 120 + 120, decay=random.random() * 3 + 1, color=random.choice([(254, 252, 211), (38, 27, 46)]), z=0), 'vfx')

    def decay_render(self, offset):
        skip = False
        if self.pos in self.parent.machine_map:
            if (self.type not in STABLE_MACHINES) and (self.pos not in self.parent.last_machine_map):
                self.alive_for = 0
            else:
                skip = True
        if not skip:
            self.alive_for = min(1 / 20, self.alive_for)
            self.alive_for = max(0, self.alive_for - self.parent.e['Window'].dt)
        self.size = [min(1, self.alive_for * 20), min(1, self.alive_for * 30)]
        self.render(offset)

    def render(self, offset):
        tile_size = self.parent.e['Tilemap'].tile_size
        rpos = [self.pos[0] * tile_size - offset[0] + MACHINE_OFFSETS[self.type][0], self.pos[1] * tile_size - offset[1] + MACHINE_OFFSETS[self.type][1]]
        if self.hurt:
            rpos[0] += random.randint(0, 4) - 2
            rpos[1] += random.randint(0, 4) - 2
        src_img = self.parent.e['Assets'].images['machines'][self.type]

        white_type = self.type + '_white'
        if white_type in self.parent.e['Assets'].images['machines']:
            self.parent.e['HUD'].machine_mask_src.blit(self.parent.e['Assets'].images['machines'][white_type], rpos)

        if min(self.size) > 0:
            img = pygame.transform.scale(src_img, (src_img.get_width() * self.size[0], src_img.get_height() * self.size[1]))
            rpos[0] += (src_img.get_width() - img.get_width()) / 2
            rpos[1] += (src_img.get_height() - img.get_height()) / 2
            self.parent.e['Renderer'].blit(img, rpos, z=self.pos[1])

        if self.parent.e['State'].effect_active('freeze') or self.freeze:
            ice_img = self.parent.e['Assets'].images['misc']['ice']
            self.parent.e['Renderer'].blit(ice_img, (self.pos[0] * tile_size - offset[0], self.pos[1] * tile_size - offset[1] - 7), z=self.pos[1] + 0.01)

        if self.type == 'beacon':
            center = (rpos[0] + tile_size / 2, rpos[1] + tile_size / 2)
            for i, angle in enumerate([self.parent.e['Window'].time * 4, self.parent.e['Window'].time * 4 + math.pi / 4]):
                top = (center[0], center[1] - 50)
                triangles = [
                    [
                        pp.utils.game_math.advance(list(center), angle, 9),
                        top,
                        pp.utils.game_math.advance(list(center), angle + math.pi / 2, 9),
                    ],
                    [
                        pp.utils.game_math.advance(list(center), angle + math.pi / 2, 9),
                        top,
                        pp.utils.game_math.advance(list(center), angle + math.pi, 9),
                    ],
                    [
                        pp.utils.game_math.advance(list(center), angle + math.pi, 9),
                        top,
                        pp.utils.game_math.advance(list(center), angle + math.pi * 3 / 2, 9),
                    ],
                    [
                        pp.utils.game_math.advance(list(center), angle, 9),
                        top,
                        pp.utils.game_math.advance(list(center), angle + math.pi * 3 / 2, 9),
                    ],
                ]
                for triangle in triangles:
                    self.parent.e['Renderer'].renderf(pygame.draw.polygon, (38, 27, 46) if i == 0 else (254, 252, 211), triangle, width=1, group='default', z=self.pos[1] + 0.5)

class Machines(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        self.step_interval = 0.15

        self.activation_groups = 16
        self.activation_rate = 1.5

        self.high_life_cooldown = 15
        self.high_life_duration = 18

        self.patterns = {}
        for pattern in self.e['Assets'].images['patterns']:
            self.patterns[pattern] = []
            for rot in {0, 90, 180, 270}:
                self.patterns[pattern].append(pygame.transform.rotate(self.e['Assets'].images['patterns'][pattern], rot))

        Automata()
        
        self.reset(soft=True)

    @property
    def high_life(self):
        return max(0, self.high_life_timer)
    
    @property
    def high_life_time(self):
        return self.high_life_duration - self.high_life

    def reset(self, soft=False):
        self.active = False

        self.recent_spawns = []

        self.last_machine_map = {}
        self.machine_map = {}

        self.no_enemy_dur = 0

        self.activation_index = 0
        self.activation_timer = 0

        self.steps_since_pause = 0
        self.pause = 0

        self.last_step = time.time()
        self.wave_start = time.time()

        self.beacon = None

        self.high_life_timer = -self.high_life_cooldown

        if not soft:
            self.new_wave()
        else:
            self.minimap = self.e['Tilemap'].minimap_base.copy()
            self.minimap.set_alpha(180)

        self.e['Automata'].update_dimensions(self.e['Tilemap'].dimensions)

        self.machines_in_range = []

    def new_wave(self):
        self.e['Music'].play('summer_battle')

        self.active = True

        self.e['Game'].player.height = 200

        self.e['State'].wave += 1

        self.e['State'].clear_map()

        load_successful = self.e['Tilemap'].load_random_map()
        if not load_successful:
            return

        if self.e['State'].wave == 10:
            self.e['EntityGroups'].add(Frenemy('jim', (350, 300)), 'frenemies')

        self.e['Game'].player.pos = list(self.e['Tilemap'].spawn)
        if self.e['Game'].player.partner[0]:
            self.e['Game'].player.partner[0].pos = self.e['Game'].player.pos.copy()
            self.e['Game'].player.partner[0].height = self.e['Game'].player.height

        self.minimap = self.e['Tilemap'].minimap_base.copy()
        self.minimap.set_alpha(180)

        self.high_life_timer = -10

        self.e['State'].notify(f'Wave {self.e["State"].wave}')

        self.wave_start = time.time()
        self.pause = 5

        wave_mod = self.e['State'].wave % 10
        if (wave_mod % 4 == 0) and wave_mod:
            # beacon wave
            middle = (int(self.e['Tilemap'].dimensions[0] // 2), int(self.e['Tilemap'].dimensions[1] // 2))
            spawn_r = pygame.Rect(middle[0] - 1, middle[1] - 1, 3, 3)
            self.recent_spawns.append(spawn_r)
            self.machine_map[middle] = Machine(self, 'beacon', middle)
            self.beacon = self.machine_map[middle]

        difficulty = int(self.e['State'].wave * 3 + 4 * self.e['State'].difficulty_status['count'])
        tries = 0
        while difficulty > 0:
            choice = random.choice(list(SEASON_PATTERNS[self.e['State'].season]))
            if PATTERN_DIFFICULTY[choice] <= difficulty:
                difficulty -= PATTERN_DIFFICULTY[choice]
                if not self.place_spawn(choice):
                    difficulty += PATTERN_DIFFICULTY[choice]
                else:
                    tries = 0
            tries += 1
            if tries > 1000:
                break

        for i in range(min(self.e['State'].wave, random.randint(2, 3))):
            self.place_spawn('chest', machine_type='chest')
        
        area = self.e['Tilemap'].dimensions[0] * self.e['Tilemap'].dimensions[1]
        stump_count = int(area / 500 * (random.random() + 0.2))
        for i in range(stump_count):
            self.place_spawn('chest', machine_type='stump')

        if self.e['State'].wave != 1:
            self.e['State'].score += 220

    def end_wave(self):
        self.active = False
        self.e['State'].shop()

    def midwave_spawn(self, pattern, machine_type=None):
        self.recent_spawns = [pygame.Rect(self.e['Game'].player.center[0] // self.e['Tilemap'].tile_size - 2, self.e['Game'].player.center[1] // self.e['Tilemap'].tile_size - 2, 5, 5)]
        self.place_spawn(pattern, machine_type=machine_type)

    def place_spawn(self, pattern, machine_type=None):
        pattern = random.choice(self.patterns[pattern])
        for i in range(10):
            spawn = (random.randint(3, self.e['Tilemap'].dimensions[0] - 3 - pattern.get_width()), random.randint(3, self.e['Tilemap'].dimensions[1] - 3 - pattern.get_height()))
            spawn_r = pygame.Rect(*spawn, *pattern.get_size())
            valid = True
            for rect in self.recent_spawns:
                if rect.colliderect(spawn_r):
                    valid = False
            if valid:
                self.recent_spawns.append(spawn_r)
                if self.spawn(pattern, spawn, machine_type=machine_type):
                    return True

    def machine_by_px(self, pos_px):
        tile_size = self.e['Tilemap'].tile_size
        loc = (int(pos_px[0] // tile_size), int(pos_px[1] // tile_size))
        if loc in self.machine_map:
            return self.machine_map[loc]

    def spawn(self, pattern, pos, machine_type=None):
        if not machine_type:
            # fall just starts with spawners
            if self.e['State'].season == 'fall':
                machine_type = 'spawner'
            else:
                machine_types = WEIGHTED_MACHINE_TYPES[:8]
                if self.e['State'].wave < 3:
                    machine_types = WEIGHTED_MACHINE_TYPES[:3]
                elif self.e['State'].wave < 4:
                    machine_types = WEIGHTED_MACHINE_TYPES[:4]
                machine_type = random.choice(machine_types)
        if type(pattern) != pygame.Surface:
            pattern = random.choice(self.patterns[pattern])

        # check to avoid spawning in walls
        valid = True
        for y in range(pattern.get_height()):
            for x in range(pattern.get_width()):
                lookup_pos = (x, y)
                if pattern.get_at(lookup_pos)[:3] == (255, 255, 255):
                    spawn_pos = (x + pos[0], y + pos[1])
                    if (spawn_pos in self.e['Tilemap'].solids) or (spawn_pos in self.e['Tilemap'].gaps):
                        valid = False
                        break
            if not valid:
                break
        
        if valid:
            for y in range(pattern.get_height()):
                for x in range(pattern.get_width()):
                    lookup_pos = (x, y)
                    if pattern.get_at(lookup_pos)[:3] == (255, 255, 255):
                        spawn_pos = (x + pos[0], y + pos[1])
                        if spawn_pos not in self.machine_map:
                            self.machine_map[spawn_pos] = Machine(self, machine_type, spawn_pos)
            return True

    def step(self, activate_cycle=False):
        if len(self.machine_map):
            self.e['Sounds'].play('tick', volume=0.12)

            if self.e['State'].season == 'fall':
                self.e['Automata'].current_automata = 'brain'
            else:
                if self.high_life:
                    self.e['Automata'].current_automata = 'highlife'
                else:
                    self.e['Automata'].current_automata = 'cgol'

            self.e['Automata'].clear()
            automata_surf = self.e['Automata'].automata_map
            for loc in self.machine_map:
                automata_surf.set_at(loc, (MACHINE_ID[self.machine_map[loc].type], self.machine_map[loc].green_stat, 0, 255))
            
            self.e['Automata'].step()

            self.minimap = self.e['Tilemap'].minimap_base.copy()

            old_machine_map = self.machine_map.copy()
            self.machine_map = {}
            activate_list = []

            automata_surf = self.e['Automata'].automata_map
            for y in range(automata_surf.get_height()):
                for x in range(automata_surf.get_width()):
                    loc = (x, y)
                    src_color = automata_surf.get_at(loc)
                    if src_color[0] > 0:
                        if (loc not in self.e['Tilemap'].solids) and (loc not in self.e['Tilemap'].gaps):
                            if loc in old_machine_map:
                                self.machine_map[loc] = old_machine_map[loc]
                                self.machine_map[loc].green_stat = src_color[1]
                            else:
                                self.machine_map[loc] = Machine(self, INV_MACHINE_ID[src_color[0]], loc, green=src_color[1])
                                activate_list.append(loc)
                            if INV_MACHINE_ID[src_color[0]] in STABLE_MACHINES:
                                if INV_MACHINE_ID[src_color[0]] == 'stump':
                                    self.minimap.set_at(loc, (100, 97, 139))
                                else:
                                    self.minimap.set_at(loc, (191, 60, 96))
                            else:
                                self.minimap.set_at(loc, (254, 252, 211))

            if activate_cycle:
                for loc in activate_list:
                    if random.random() < 0.5:
                        self.machine_map[loc].activate()
            
            self.last_machine_map = old_machine_map

            self.minimap.set_alpha(180)

    @property
    def active_enemies_remaining(self):
        if len(self.machine_map):
            return True
        if ('enemies' in self.e['EntityGroups'].groups) and len(self.e['EntityGroups'].groups['enemies']):
            return True
        if ('frenemies' in self.e['EntityGroups'].groups) and len([f for f in self.e['EntityGroups'].groups['frenemies'] if (not f.friendly) and f.health]):
            return True
        return False

    @property
    def enemies_remaining(self):
        if len(self.machine_map):
            return True
        if ('enemies' in self.e['EntityGroups'].groups) and len(self.e['EntityGroups'].groups['enemies']):
            return True
        if ('frenemies' in self.e['EntityGroups'].groups) and len([f for f in self.e['EntityGroups'].groups['frenemies'] if not f.friendly]):
            return True
        return False
    
    def paused_update(self):
        self.last_step += self.e['Window'].dt
        self.wave_start += self.e['Window'].dt

    def update(self):
        self.recent_spawns = []

        if (not self.e['State'].title) and self.active and (not self.e['State'].ui_busy):
            if not self.enemies_remaining:
                if not self.e['State'].shopping:
                    self.no_enemy_dur += self.e['Window'].dt
                    if self.no_enemy_dur > 4:
                        self.end_wave()
                        self.last_machine_map = self.machine_map
                        self.no_enemy_dur = 0

        if not self.e['Game'].player.moved:
            self.last_step = time.time()
            self.wave_start = time.time()

        self.high_life_timer -= self.e['Window'].dt
        if (self.high_life_timer + self.e['Window'].dt > 0) and (self.high_life_timer <= 0):
            self.e['Sounds'].play('highlife_transition')
            self.e['State'].notify('Machines Returned to Normal')
            self.e['HUD'].flash = 1
            self.e['Sounds'].sounds['ambience'].set_volume(self.e['Settings'].sfx_volume * 0.6)
            self.e['Music'].play('summer_battle', start=self.e['Window'].time, fadein=1.0)

        if (self.high_life_timer > 0) and (self.high_life_timer < 0.5):
            self.e['Music'].fadeout(0.5)

        if (not self.pause) and (not self.e['State'].effect_active('freeze')) and (not (self.e['Transition'].progress or self.e['Transition'].level_end)) and (not self.e['State'].title):
            if time.time() - self.last_step > self.step_interval:
                self.step(self.steps_since_pause % max(4, math.ceil(8 - self.e['State'].difficulty / 50)) == 0)
                self.last_step = time.time()
                if self.steps_since_pause == 0:
                    if self.beacon and (self.high_life_timer <= -self.high_life_cooldown) and (random.random() < 0.2):
                        self.high_life_timer = self.high_life_duration
                        self.e['Sounds'].play('highlife_transition')
                        self.e['State'].notify(f'Machine Event: {EVENT_NAMES[self.e["State"].season]}')
                        self.e['HUD'].flash = 1
                        self.e['Sounds'].sounds['ambience'].set_volume(0.02)
                        self.e['Music'].play('highlife')

                difficulty = self.e['State'].wave * 3 + 4
                if self.beacon and (len(self.machine_map) < difficulty * 3) and (random.random() < 0.1):
                    self.midwave_spawn(random.choice(MINOR_PATTERNS))

                if (len(self.machine_map) > 45) and (random.random() < 0.02):
                    self.midwave_spawn('chest', machine_type='chest')

                bb_activate_interval = 3 if self.high_life else 7
                if (not (self.steps_since_pause % bb_activate_interval)) and (self.e['State'].season == 'fall'):
                    # let spawners spawn any of the first 6 machine types
                    self.e['Automata'].uniforms['spawner_spawn_id'] = random.randint(100, 105)
                else:
                    self.e['Automata'].uniforms['spawner_spawn_id'] = 0

                self.steps_since_pause += 1
                if self.steps_since_pause >= 16:
                    self.steps_since_pause = 0
                    self.pause = self.e['State'].difficulty_status['pause']
        else:
            self.pause = max(0, self.pause - self.e['Window'].dt)

        activate = False
        self.activation_timer += self.e['Window'].dt
        while self.activation_timer > 1 / self.activation_rate:
            self.activation_timer -= 1 / self.activation_rate
            self.activation_index = (self.activation_index + 1) % self.activation_groups
            activate = True

        for machine in list(self.machine_map.values()):
            machine.update(activate)

    def render(self):
        for machine in self.machine_map.values():
            machine.render(self.e['Game'].camera)

        if time.time() - self.last_step < 1 / 20:
            for machine in self.last_machine_map.values():
                machine.decay_render(self.e['Game'].camera)