import math
import random

import pygame

from . import pygpen as pp
from .rig import CentipedeRig
from .animation import Animation

class Debris(pp.Element):
    def __init__(self, debris_type, pos, force=0.6):
        super().__init__()

        self.type = debris_type

        self.pos = [pos[0], pos[1], 0]

        self.angle = random.random() * math.pi * 2
        self.speed = (random.random() * 70 + 40) * force
        self.v_speed = random.random() * 120 + 40

        self.life = 5
        if self.type == 'shell':
            self.life = 3

        self.rotation = 0
        self.v_speed_dir = random.choice([-1, 1])

        self.speed_decay = 100
        self.gravity = 200

    def update(self, dt):
        self.pos[0] += math.cos(self.angle) * self.speed * dt
        self.pos[1] += math.sin(self.angle) * self.speed * dt
        self.pos[2] += self.v_speed * dt

        self.speed = pp.utils.game_math.normalize(self.speed, self.speed_decay * dt)
        self.v_speed -= self.gravity * dt

        self.life = max(0, self.life - dt)
        if not self.life:
            return True

        if self.pos[2] < 0:
            if abs(self.v_speed) > 20:
                self.pos[2] *= -1
                self.v_speed *= -0.5
            else:
                self.pos[2] = 0
                self.v_speed = 0

        self.rotation -= math.cos(self.angle) * (self.speed + abs(self.v_speed) * self.v_speed_dir * 0.5) * dt * 20

    @property
    def img(self):
        return self.e['Assets'].images['debris'][self.type]

    def renderz(self, offset=(0, 0), group='default'):
        shadow_img = self.e['Assets'].images['misc']['shadow_tiny' if self.type == 'shell' else 'shadow_small']
        img = pygame.transform.rotate(self.img, self.rotation)
        if (self.life > 2) or (random.random() > 0.5):
            self.e['Renderer'].blit(img, (self.pos[0] - offset[0] - img.get_width() // 2, self.pos[1] - self.pos[2] - offset[1] - img.get_height() // 2), group=group, z=self.pos[1] / self.e['Tilemap'].tile_size)
        self.e['Renderer'].blit(shadow_img, (self.pos[0] - offset[0] - shadow_img.get_width() // 2, self.pos[1] - offset[1] - shadow_img.get_height() // 2 + img.get_height() // 2), group=group, z=self.pos[1] / self.e['Tilemap'].tile_size)

ABILITY_DURATIONS = {
    'invincibility': 5,
    'lifesteal': 12,
    'collateral': 12,
    'double_barrel': 15,
    'freeze': 7,
    'extra_rounds': 8,
}

class Grenade(Debris):
    def __init__(self, pos, target, subtype='grenade', speed=120, gravity=450):
        super().__init__(subtype, pos)

        self.target = target
        self.angle = math.atan2(target[1] - pos[1], target[0] - pos[0])
        self.speed = speed
        self.speed_decay = 0
        self.gravity = gravity

        dis = pp.utils.game_math.distance(pos, target)
        travel_time = dis / self.speed

        self.v_speed = travel_time * self.gravity / 2

    def explode(self):
        spark_colors = [(238, 209, 108), (228, 103, 71), (38, 27, 46), (254, 252, 211), (191, 60, 96)]
        self.e['EntityGroups'].add(pp.vfx.Circle(self.pos, velocity=150, decay=2.5, width=4, radius=0, color=(254, 252, 211), z=5980), 'vfx')
        self.e['EntityGroups'].add(pp.vfx.Circle(self.pos, velocity=220, decay=2.7, width=8, radius=0, color=(228, 103, 71), z=5979), 'vfx')
        self.e['EntityGroups'].add(pp.vfx.Circle(self.pos, velocity=350, decay=2.9, width=6, radius=0, color=(38, 27, 46), z=5978), 'vfx')
        for i in range(40):
            self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, random.random() * math.pi * 2, size=(random.randint(5, 9), random.randint(1, 2)), speed=random.random() * 120 + 120, decay=random.random() * 3 + 0.5, color=random.choice(spark_colors), z=5981), 'vfx')
        for machine in list(self.e['Machines'].machine_map.values()):
            if pp.utils.game_math.distance(machine.center, self.pos) < 48:
                machine.damage(5)
        if 'enemies' in self.e['EntityGroups'].groups:
            for entity in self.e['EntityGroups'].groups['enemies']:
                if type(entity) == CentipedeRig:
                    if pp.utils.game_math.distance(entity.segments[0], self.pos) < 48:
                        entity.damage(5)
        self.e['Game'].player.play_from('boom', self.pos, volume=1.0)

    def update(self, dt):
        old_v = self.v_speed
        super().update(dt)

        if old_v < self.v_speed:
            self.explode()
            return True
        
class Bomb(Grenade):
    def __init__(self, pos, target):
        super().__init__(pos, target, subtype='bomb')

    def explode(self):
        spark_colors = [(38, 27, 46), (254, 252, 211)]
        for i in range(10):
            self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, random.random() * math.pi * 2, size=(random.randint(5, 9), 1), speed=random.random() * 120 + 120, decay=random.random() * 3 + 0.5, color=random.choice(spark_colors), z=5981), 'vfx')
        for i in range(random.randint(12, 16)):
            anim = Animation('flash', (self.pos[0] + random.randint(-8, 8), self.pos[1] + random.randint(-8, 8)))
            anim.animation.update(random.random() * 0.3 + 0.3)
            anim.flip[0] = random.choice([True, False])
            self.e['EntityGroups'].add(anim, 'vfx')
        anim = Animation('small_explosion', (self.pos[0], self.pos[1]))
        anim.flip[0] = random.choice([True, False])
        self.e['EntityGroups'].add(anim, 'vfx')
        
        player = self.e['Game'].player
        if player.partner[0] and player.partner[0].health:
            if (pp.utils.game_math.distance(player.partner[0].center, self.pos) < 12) and (not player.partner[0].rolling):
                player.partner[0].damage(1)
        if (pp.utils.game_math.distance(player.center, self.pos) < 12) and (not player.rolling):
            player.damage(1)

        self.e['Game'].player.play_from('small_boom', self.pos, volume=0.5)

    def renderz(self, offset=(0, 0), group='default'):
        super().renderz(offset=offset, group=group)
        marker = self.e['Assets'].images['misc']['bomb_marker']
        self.e['Renderer'].blit(marker, (self.target[0] - marker.get_width() / 2 - offset[0], self.target[1] - marker.get_height() / 2 - offset[1]), z=-5.4)

class AbilityDrop(Debris):
    def __init__(self, ability_type, pos, force=0.6):
        super().__init__(ability_type, pos, force=force)

        self.life = 20

    @property
    def img(self):
        return self.e['Assets'].images['upgrades'][f'{self.type}_b']

    def update(self, dt):
        super().update(dt)

        self.rotation = 0

        dis = pp.utils.game_math.distance(self.e['Game'].player.center, (self.pos[0], self.pos[1] + self.img.get_height() / 2))
        if dis < 12:
            self.e['State'].add_effect(self.type, ABILITY_DURATIONS[self.type])
            self.e['Sounds'].play('powerup', volume=0.45)
            for i in range(12):
                self.e['EntityGroups'].add(pp.vfx.Spark(self.pos, random.random() * math.pi * 2, size=(random.randint(4, 6), 1), speed=random.random() * 80 + 60, decay=random.random() * 3 + 2, color=(254, 252, 211), z=0), 'vfx')
            return True
