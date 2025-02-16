import math
import random

import pygame

from . import pygpen as pp

from .slash import Slash
from .tempterrain import TempTerrain

class Bullet(pp.Element):
    def __init__(self, bullet_type, pos, angle, speed=None, advance=8, base_range=0.4, damage=1, piercing=False, src_weapon=None, custom_projectile=None):
        super().__init__()

        self.type = bullet_type
        self.pos = list(pos)
        self.angle = angle % (math.pi * 2)
        self.speed = min(speed if speed else 280, self.e['State'].difficulty_status['bullet_speed'])
        self.damage = damage
        self.piercing = piercing
        self.hit_targets = set()
        self.life = 10
        self.bounces = 0
        self.src_weapon = src_weapon
        self.custom_projectile = custom_projectile

        if self.type in {'blue', 'brown'}:
            self.bounces = self.e['State'].owned_upgrades['ricochet']
            self.speed = (speed if speed else 350) * (1.15 ** self.e['State'].owned_upgrades['winged_bullets'])
            self.life = (base_range * (350 / self.speed)) * (1.1 ** self.e['State'].owned_upgrades['scoped_weapons']) / (1.15 ** self.e['State'].owned_upgrades['winged_bullets'])

        self.pos = pp.game_math.advance(self.pos, self.angle, advance)

        for i in range(5):
            self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, self.angle + random.random() * 1.5 - 0.75, size=(random.randint(4, 6), 1), speed=random.random() * 100 + 120, decay=random.random() * 9 + 4, color=(254, 252, 211), z=0), 'vfx')

    def collision_sparks(self, angle_offset=math.pi):
        for i in range(5):
            self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, self.angle + random.random() * 1.5 - 0.75 + angle_offset, size=(random.randint(4, 6), 1), speed=random.random() * 100 + 120, decay=random.random() * 9 + 4, color=(254, 252, 211), z=0), 'vfx')

    def die(self, damaged=False, angle_offset=math.pi):
        if damaged:
            self.e['EntityGroups'].add(Slash(self.pos, self.angle + random.random() - 0.5, (20, 2)), 'vfx')
        self.collision_sparks(angle_offset=angle_offset)

    def attempt_damage(self, target, friendly=True):
        dmg = self.damage
        if target not in self.hit_targets:
            if self.src_weapon and friendly:
                if random.random() < self.src_weapon.enchant_stat('precision'):
                    dmg *= 2
                    self.e['Sounds'].play('critical', volume=1.0)
                if random.random() < self.src_weapon.enchant_stat('vampirism'):
                    self.e['Game'].player.heal(dmg * 0.1)
                    self.e['Sounds'].play('drain', volume=1.0)
            if target.damage(dmg):
                target.kb_stack.append([self.angle, 100])
            if not self.piercing:
                self.die(damaged=True)
                return True
            self.hit_targets.add(target)

    def update(self, dt):
        # handle movement with bounces
        movement = [math.cos(self.angle) * self.speed * dt, math.sin(self.angle) * self.speed * dt]
        self.pos[0] += movement[0]
        if self.e['Tilemap'].solid_check(self.pos, include_gaps=False):
            if self.bounces:
                self.bounces -= 1
                movement[0] *= -1
                self.collision_sparks()
                self.angle = math.atan2(movement[1], movement[0])
                self.pos[0] += movement[0]
                self.e['Game'].player.play_from('ricochet', self.pos, volume=0.7)
            else:
                self.die()
                return True
        self.pos[1] += movement[1]
        if self.e['Tilemap'].solid_check(self.pos, include_gaps=False):
            if self.bounces:
                self.bounces -= 1
                movement[1] *= -1
                self.collision_sparks()
                self.angle = math.atan2(movement[1], movement[0])
                self.pos[1] += movement[1]
                self.e['Game'].player.play_from('ricochet', self.pos, volume=0.25)
            else:
                self.die()
                return True

        self.life = max(0, self.life - self.e['Window'].dt)
        if not self.life:
            self.die(angle_offset=0)
            return True
        
        for i in range(5):
            if self.piercing and (random.random() / 60 < dt):
                self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, self.angle + math.pi + random.random() * 1.5 - 0.75, size=(random.randint(4, 6), 1), speed=random.random() * 100 + 120, decay=random.random() * 9 + 4, color=random.choice([(254, 252, 211), (74, 156, 223)]), z=0), 'vfx')

        if self.type != 'red':
            machine = self.e['Machines'].machine_by_px(self.pos)
            if machine:
                if self.attempt_damage(machine):
                    return True
            
            if 'enemies' in self.e['EntityGroups'].groups:
                for enemy in self.e['EntityGroups'].groups['enemies']:
                    if pp.utils.game_math.distance(self.pos, enemy.segments[0]) < 10:
                        if self.attempt_damage(enemy):
                            return True
            
            if 'frenemies' in self.e['EntityGroups'].groups:
                for frenemy in self.e['EntityGroups'].groups['frenemies']:
                    if (not frenemy.friendly) and (pp.utils.game_math.distance(self.pos, frenemy.pos) < 10):
                        if self.attempt_damage(frenemy):
                            return True
        
        if self.type == 'red':
            player = self.e['Game'].player
            if player.partner[0] and player.partner[0].health:
                if player.partner[0].rect.collidepoint(self.pos) and (not player.partner[0].rolling):
                    if self.attempt_damage(player.partner[0], friendly=False):
                        return True
            if player.hitbox.collidepoint(self.pos) and (not player.rolling):
                if self.attempt_damage(player, friendly=False):
                    return True

    def renderz(self, offset=(0, 0), group='default'):
        if self.e['Game'].camera.rect_exp.collidepoint(self.pos):
            if self.custom_projectile:
                img = pygame.transform.rotate(self.e['Assets'].images['projectiles'][self.custom_projectile], -math.degrees(self.angle))
            else:
                img = self.e['Assets'].bullets[self.type][-int(round(math.degrees(self.angle)))]
            self.e['Renderer'].blit(img, (self.pos[0] - offset[0] - img.get_width() // 2, self.pos[1] - offset[1] - img.get_height() // 2), group=group, z=5990)
            shadow_img = self.e['Assets'].images['misc']['shadow_small']
            self.e['Renderer'].blit(shadow_img, (self.pos[0] - offset[0] - shadow_img.get_width() // 2, self.pos[1] - offset[1] - shadow_img.get_height() // 2 + 3), group=group, z=5989)

class Arrow(Bullet):
    pass

class WarpBullet(Bullet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_valid_tile = None

    def update(self, dt):
        if not self.e['Tilemap'].solid_check(self.pos):
            self.last_valid_tile = (int(self.pos[0] // self.e['Tilemap'].tile_size), int(self.pos[1] // self.e['Tilemap'].tile_size))

        killed = super().update(dt)

        if killed and self.last_valid_tile:
            if self.src_weapon:
                self.src_weapon.warp_mark = ((self.last_valid_tile[0] + 0.5) * self.e['Tilemap'].tile_size, (self.last_valid_tile[1] + 0.5) * self.e['Tilemap'].tile_size)
        
        return killed

class QuakeBullet(Bullet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_valid_tile = None

        self.effect_range = 3

    def update(self, dt):
        if not self.e['Tilemap'].solid_check(self.pos):
            self.last_valid_tile = (int(self.pos[0] // self.e['Tilemap'].tile_size), int(self.pos[1] // self.e['Tilemap'].tile_size))

        killed = super().update(dt)

        spark_colors = [(193, 159, 113), (149, 86, 68), (106, 51, 60)]
        for i in range(5):
            if random.random() / 60 < dt:
                self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, self.angle + math.pi + random.random() * 1.5 - 0.75, size=(random.randint(4, 6), 1), speed=random.random() * 100 + 120, decay=random.random() * 9 + 4, color=random.choice(spark_colors), z=0), 'vfx')

        if killed and self.last_valid_tile:
            base = (int(self.pos[0] // self.e['Tilemap'].tile_size), int(self.pos[1] // self.e['Tilemap'].tile_size))
            for i in range(self.effect_range * 2 + 1):
                for j in range(self.effect_range * 2 + 1):
                    x = i - self.effect_range
                    y = j - self.effect_range
                    loc = (base[0] + x, base[1] + y)
                    # the -0.5 increases odds heavily near the center
                    dis = max(0, pp.game_math.distance((0, 0), (x, y)) - 0.5)
                    dis_ratio = dis / (self.effect_range * math.sqrt(2))
                    if random.random() < (1 - dis_ratio) ** 2:
                        self.e['EntityGroups'].add(TempTerrain((0, 0), loc), 'entities')
            self.e['Game'].player.play_from('small_boom', self.pos, volume=0.5)

        return killed