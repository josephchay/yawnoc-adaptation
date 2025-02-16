import math
import random

import pygame

from . import pygpen as pp
from .bullet import Bullet, QuakeBullet, WarpBullet, Arrow
from .debris import Debris, Grenade, ABILITY_DURATIONS
from .animation import Animation

WEAPON_NAMES = {
    'rifle': 'Rifle',
    'pistol': 'Pistol',
    'shotgun': 'Shotgun',
    'quaker': 'Quaker',
    'warpgun': 'Warpgun',
    'bow': 'Bow',
    'beamer': 'Beamer'
}

ENCHANTS = {
    'vampirism': {
        'title': 'Vampiric',
        'name': 'Vampirism',
        'growth': 'exponential',
        'growth_factor': 1.005,
        'text': '<stat>% chance to heal upon dealing damage.'
    },
    'precision': {
        'title': 'Precise',
        'name': 'Precision',
        'growth': 'exponential',
        'growth_factor': 1.035,
        'text': '<stat>% chance to critically strike.'
    },
    'overload': {
        'title': 'Overloaded',
        'name': 'Overload',
        'growth': 'exponential',
        'growth_factor': 1.025,
        'text': '<stat>% chance to double fire.'
    },
}

WEAPON_STATS = {
    'rifle': {
        'name': 'Rifle',
        'desc': 'A standard rifle. It\'s a well rounded weapon.',
        'base_price': 100,
        'firerate': 8,
        'range': 0.4,
        'inaccuracy': 0.135,
        'damage': 1,
        'shots': 1,
        'advance': 20,
        'speed': 370,
        'primary': 'shoot',
        'secondary': 'piercing_round',
        'secondary_cooldown': 6,
        'shot_sound': 'shoot',
        'animated': False,
    },
    'pistol': {
        'name': 'Pistol',
        'desc': 'A small sidearm that comes with a grenade.',
        'base_price': 100,
        'firerate': 4.5,
        'range': 0.55,
        'damage': 1.5,
        'inaccuracy': 0.07,
        'shots': 1,
        'advance': 9,
        'speed': 320,
        'primary': 'shoot',
        'secondary': 'grenade',
        'secondary_cooldown': 10,
        'shot_sound': 'pistol_shoot',
        'animated': False,
    },
    'shotgun': {
        'name': 'Shotgun',
        'desc': 'A shotgun. Inaccurate, but powerful at close range.',
        'base_price': 100,
        'firerate': 2,
        'range': 0.2,
        'inaccuracy': 0.4,
        'damage': 1,
        'shots': 7,
        'advance': 19,
        'speed': 250,
        'primary': 'shoot',
        'secondary': 'birdshot',
        'secondary_cooldown': 8,
        'shot_sound': 'shotgun_shoot',
        'animated': False,
    },
    'quaker': {
        'name': 'Quaker',
        'desc': 'A bulky weapon that can raise up earth.',
        'base_price': 80,
        'firerate': 1.3,
        'range': 0.3,
        'inaccuracy': 0.2,
        'damage': 5,
        'shots': 1,
        'advance': 17,
        'speed': 150,
        'primary': 'shoot',
        'secondary': 'quake',
        'secondary_cooldown': 2.5,
        'shot_sound': 'pistol_shoot',
        'animated': False,
    },
    'warpgun': {
        'name': 'Warpgun',
        'desc': 'A strangely shaped weapon capable of warping space.',
        'base_price': 50,
        'firerate': 0.7,
        'range': 0.5,
        'inaccuracy': 0.1,
        'damage': 3,
        'shots': 1,
        'advance': 12,
        'speed': 450,
        'primary': 'warp_mark',
        'secondary': 'warp',
        'secondary_cooldown': 0.5,
        'shot_sound': 'pistol_shoot',
        'animated': False,
    },
    'bow': {
        'name': 'Bow',
        'desc': 'A bow crafted out of local flora.',
        'base_price': 170,
        'firerate': 2,
        'range': 1.0,
        'inaccuracy': 0.04,
        'damage': 3,
        'shots': 1,
        'advance': 7,
        'speed': 350,
        'primary': 'arrow_shoot',
        'secondary': 'arrow_barrage',
        'secondary_cooldown': 6,
        'shot_sound': 'arrow_fire',
        'animated': True,
    },
    'beamer': {
        'name': 'Beamer',
        'desc': 'A strong rifle with an extremely high rate of fire.',
        'base_price': 200,
        'firerate': 20,
        'range': 0.375,
        'inaccuracy': 0.135,
        'damage': 0.5,
        'shots': 1,
        'advance': 20,
        'speed': 370,
        'primary': 'shoot',
        'secondary': 'extra_rounds',
        'secondary_cooldown': 28,
        'shot_sound': 'shoot',
        'animated': False,
    },
}

class Weapon(pp.Element):
    def __init__(self, weapon_type, owner):
        super().__init__()

        self.type = weapon_type
        self.owner = owner

        self.shoot_cooldown = [0, 1]
        self.secondary_cooldown = [0, 1]

        self.attempting_fire = [False, False]
        self.last_charge = 0

        if self.type not in self.e['State'].weapon_enchants:
            self.enchants = {enchant: [0, 0] for enchant in ENCHANTS}
        else:
            self.enchants = {enchant: (self.e['State'].weapon_enchants[self.type][enchant] if enchant in self.e['State'].weapon_enchants[self.type] else [0, 0]) for enchant in ENCHANTS}

        self.animation = None
        if WEAPON_STATS[self.type]['animated']:
            self.animation = self.e['EntityDB']['weapons'].animations[self.type].copy()

        self.reset()

    def reset(self):
        self.warp_mark = None

    def enchant(self):
        if not len(self.enchant_list):
            count = 2
            if random.random() < 0.05:
                count = 3
            for enchant in range(count):
                available_enchants = list(set(list(ENCHANTS)) - set([enchant[1] for enchant in self.enchant_list]))
                if available_enchants:
                    enchant_type = random.choice(available_enchants)
                    self.enchants[enchant_type] = [1 if enchant == 0 else 0.5, 1]
        else:
            for enchant in self.enchants:
                if self.enchants[enchant][0]:
                    self.enchants[enchant][1] += 1
        self.save_enchants()

    def strip(self):
        # weight, level
        self.enchants = {enchant: [0, 0] for enchant in ENCHANTS}
        self.save_enchants()

    def enchant_stat(self, enchant_type):
        level = int(math.ceil(self.enchants[enchant_type][1] * self.enchants[enchant_type][0]))
        if ENCHANTS[enchant_type]['growth'] == 'exponential':
            return ENCHANTS[enchant_type]['growth_factor'] ** level - 1
        
    def save_enchants(self):
        self.e['State'].weapon_enchants[self.type] = {enchant: self.enchants[enchant] for enchant in  self.enchants if self.enchants[enchant][0]}
        self.e['State'].save()
        
    @property
    def enchant_tier(self):
        count = len(self.enchant_list)
        max_level = max([enchant[2] for enchant in self.enchant_list]) if count else 0
        return (1.4 ** max_level) * (count if count else 2)
    
    @property
    def enchant_level(self):
        return max([enchant[2] for enchant in self.enchant_list]) if len(self.enchant_list) else 0
    
    @property
    def enchant_price(self):
        return int(self.enchant_tier * 70)

    @property
    def enchant_list(self):
        return sorted([(self.enchants[enchant][0], enchant, self.enchants[enchant][1]) for enchant in self.enchants if self.enchants[enchant][0]], reverse=True)

    @property
    def name(self):
        return WEAPON_NAMES[self.type]
    
    @property
    def title(self):
        if len(self.enchant_list):
            return f'{ENCHANTS[self.enchant_list[0][1]]["title"]} {WEAPON_NAMES[self.type]}'
        return self.name

    @property
    def chargable_primary(self):
        return self.type == 'bow'

    @property
    def chargable_secondary(self):
        return self.type == 'bow'

    @property
    def firerate(self):
        return WEAPON_STATS[self.type]['firerate'] * (1.08 ** self.upgrade_stacks('extra_rounds')) * (1.65 if self.e['State'].effect_active('extra_rounds') else 1)
    
    @property
    def projectile_spawn_locs(self):
        spawn_locs = [self.owner.gun_center]
        if self.e['State'].effect_active('double_barrel') and (self.owner == self.e['Game'].player):
            spawn_locs = [pp.utils.game_math.advance(list(self.owner.gun_center), self.owner.angle + math.pi / 2, 2.5), pp.utils.game_math.advance(list(self.owner.gun_center), self.owner.angle - math.pi / 2, 2.5)]
        return spawn_locs
    
    @property
    def img(self):
        if self.animation:
            return self.animation.img
        return self.e['Assets'].images['weapons'][self.type]
    
    @property
    def base_color(self):
        return 'blue' if self.owner.friendly else 'red'
    
    @property
    def num_shots(self):
        ws = WEAPON_STATS[self.type]
        shots = ws['shots']
        if random.random() < self.enchant_stat('overload'):
            shots *= 2
        return shots
    
    @property
    def max_range(self):
        ws = WEAPON_STATS[self.type]
        return ws['range'] * 350 * (1.1 ** self.e['State'].owned_upgrades['scoped_weapons'])
    
    def upgrade_stacks(self, upgrade_id):
        return self.e['State'].owned_upgrades[upgrade_id] if self.owner.friendly else 0
    
    def spawn_shell(self):
        new_debris = Debris('shell', self.owner.center, random.random() * 0.4 + 0.7)
        new_debris.v_speed *= 0.5
        new_debris.angle = self.owner.angle + math.pi + (random.random() - 0.5)
        self.e['EntityGroups'].add(new_debris, 'vfx')
    
    def update(self, dt):
        self.shoot_cooldown[0] = max(0, self.shoot_cooldown[0] - self.e['Window'].dt)
        self.secondary_cooldown[0] = max(0, self.secondary_cooldown[0] - self.e['Window'].dt)

        if self.attempting_fire[0]:
            if self.chargable_primary:
                self.animation.update(self.firerate * self.e['Window'].dt)
                self.last_charge = 0
                if self.animation.finished:
                    ws = WEAPON_STATS[self.type]
                    if ws['primary'] == 'arrow_shoot':
                        for loc in self.projectile_spawn_locs:
                            for shot in range(self.num_shots):
                                self.e['EntityGroups'].add(Arrow(self.base_color, loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'], advance=ws['advance'], base_range=ws['range'], damage=ws['damage'], speed=ws['speed'], custom_projectile='arrow'), 'entities')

                        self.e['Sounds'].play(ws['shot_sound'], volume=0.5)
                    self.animation.reset()
        elif self.attempting_fire[1]:
            if self.chargable_secondary:
                self.animation.update(self.firerate * self.e['Window'].dt)
                self.last_charge = 1
        elif self.chargable_primary or self.chargable_secondary:
            if self.animation.finished:
                ws = WEAPON_STATS[self.type]
                if self.last_charge == 1:
                    if ws['secondary'] == 'arrow_barrage':
                        for loc in self.projectile_spawn_locs:
                            for shot in range(11):
                                angle = (shot - 5) * 0.02
                                self.e['EntityGroups'].add(Arrow(self.base_color, loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'] + angle, advance=ws['advance'], base_range=ws['range'], damage=ws['damage'], speed=ws['speed'], custom_projectile='arrow'), 'entities')
                        
                        self.e['Sounds'].play('arrow_fire', volume=1.0)
                    self.secondary_cooldown = [ws['secondary_cooldown'] * (0.86 ** self.upgrade_stacks('stopwatch'))] * 2
            self.animation.reset()

        if self.type == 'warpgun':
            if self.warp_mark:
                marker = self.e['Assets'].images['misc']['warp_marker']
                self.e['Renderer'].blit(marker, (self.warp_mark[0] - marker.get_width() / 2 - self.e['Game'].camera[0], self.warp_mark[1] - marker.get_height() / 2 - self.e['Game'].camera[1]), z=-5.39)

        self.attempting_fire = [False, False]
    
    def attempt_fire(self, damage_scale=1.0):
        if self.shoot_cooldown[0]:
            return False
        if self.chargable_primary:
            if not self.shoot_cooldown[0]:
                self.attempting_fire[0] = True
        elif not self.shoot_cooldown[0]:
            self.shoot_cooldown = [1 / self.firerate, 1 / self.firerate]

            ws = WEAPON_STATS[self.type]
            if ws['primary'] == 'shoot':
                for loc in self.projectile_spawn_locs:
                    for shot in range(self.num_shots):
                        self.e['EntityGroups'].add(Bullet(self.base_color, loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'], advance=ws['advance'], base_range=ws['range'], damage=ws['damage'] * damage_scale, speed=ws['speed'], src_weapon=self), 'entities')
                    self.spawn_shell()

                self.e['Sounds'].play(ws['shot_sound'], volume=0.25)

            if ws['primary'] == 'warp_mark':
                for loc in self.projectile_spawn_locs:
                    for shot in range(self.num_shots):
                        self.e['EntityGroups'].add(WarpBullet(self.base_color, loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'], advance=ws['advance'], base_range=ws['range'], damage=ws['damage'] * damage_scale, speed=ws['speed'], src_weapon=self), 'entities')
                
                self.e['Sounds'].play(ws['shot_sound'], volume=0.25)
        return True

    def attempt_secondary(self):
        if self.secondary_cooldown[0]:
            return False
        if self.chargable_secondary:
            if not self.secondary_cooldown[0]:
                self.attempting_fire[1] = True
        elif not self.secondary_cooldown[0]:
            ws = WEAPON_STATS[self.type]
            self.secondary_cooldown = [ws['secondary_cooldown'] * (0.86 ** self.upgrade_stacks('stopwatch'))] * 2

            secondary = ws['secondary']
            if secondary == 'extra_rounds':
                self.e['State'].add_effect('extra_rounds', ABILITY_DURATIONS['extra_rounds'])
                self.e['Sounds'].play('powerup', volume=0.45)

            if secondary == 'piercing_round':
                for loc in self.projectile_spawn_locs:
                    for shot in range(self.num_shots):
                        self.e['EntityGroups'].add(Bullet('blue', loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'], advance=ws['advance'], base_range=ws['range'], damage=ws['damage'] * 3, speed=ws['speed'], piercing=True, src_weapon=self), 'entities')
                    self.spawn_shell()

                self.e['Sounds'].play('shoot', volume=0.5)
            if secondary == 'birdshot':
                for loc in self.projectile_spawn_locs:
                    for shot in range(self.num_shots * 4):
                        self.e['EntityGroups'].add(Bullet('blue', loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'] * 2, advance=ws['advance'], base_range=ws['range'], damage=ws['damage'], speed=ws['speed'], src_weapon=self), 'entities')
                    self.spawn_shell()

                self.e['Sounds'].play('shotgun_shoot', volume=0.5)
            if secondary == 'grenade':
                self.e['EntityGroups'].add(Grenade(self.owner.center, pygame.Vector2(self.e['Game'].mpos) + self.e['Game'].camera.pos), 'entities')

                self.e['Sounds'].play('jump', volume=0.8)

            if secondary == 'quake':
                for loc in self.projectile_spawn_locs:
                    self.e['EntityGroups'].add(QuakeBullet('brown', loc, self.owner.angle + (random.random() - 0.5) * ws['inaccuracy'] * 2, advance=ws['advance'], base_range=ws['range'], damage=ws['damage'], speed=ws['speed'], src_weapon=self), 'entities')

                self.e['Sounds'].play('heavy_fire', volume=0.9)

            if secondary == 'warp':
                if self.warp_mark:
                    self.owner.pos = [self.warp_mark[0] - 4, self.warp_mark[1] - 3]
                    self.e['Sounds'].play('warp', volume=0.7)
                    for i in range(random.randint(5, 7)):
                        anim = Animation('flash', (self.owner.center[0] + random.randint(-6, 6), self.owner.center[1] + random.randint(-9, 6)))
                        anim.animation.update(random.random() * 0.6)
                        anim.flip[0] = random.choice([True, False])
                        self.e['EntityGroups'].add(anim, 'vfx')
                    spark_colors = [(74, 156, 223), (191, 60, 96), (254, 252, 211)]
                    for i in range(24):
                        self.e['EntityGroups'].add(pp.vfx.Spark(self.owner.center, random.random() * math.pi * 2, size=(random.randint(16, 20), random.randint(4, 6)), speed=random.random() * 70 + 20, decay=random.random() * 2 + 1, color=random.choice(spark_colors), z=0), 'vfx')
                else:
                    self.secondary_cooldown[0] = 0
        return True
    
    @property
    def star_rating(self):
        if self.enchant_level < 4:
            return ('bronze', self.enchant_level)
        elif self.enchant_level < 10:
            return ('silver', int((self.enchant_level - 2) // 2))
        else:
            return ('gold', int((self.enchant_level - 7) // 3))
    
    def render_stars(self, pos, group='default', z=9999):
        star_conf = self.star_rating
        for i in range(star_conf[1]):
            self.e['Renderer'].blit(self.e['Assets'].images['misc'][f'{star_conf[0]}_star'], (pos[0] + i * 4, pos[1]), group=group, z=z)
