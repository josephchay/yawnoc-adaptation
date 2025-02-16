import math
import random

import pygame

from . import pygpen as pp

from .drops import Drop
from .animation import Animation
from .bullet import Bullet
from .physics_entity import PhysicsRect

class CentipedeRig(PhysicsRect):
    def __init__(self, pos):
        super().__init__(pygame.Rect(*pos, 6, 6))

        self.z = -4

        self.spacing = 5
        self.leg_length = 7

        self.segments = []
        for i in range(12):
            self.segments.append([pos[0] + math.cos(i / 2) * 6, pos[1] + math.sin(i / 2) * 6])

        self.angle = math.pi * 3 / 2
        self.base_angle = self.angle

        self.speed = 100

        self.time = self.e['Window'].time

        self.health = 6

        self.seed = random.random() * 1000

        self.path = None
    
    @property
    def images(self):
        return self.e['Assets'].images['rigs']['centipede']
    
    @property
    def center(self):
        return self.rect.center
    
    def pull_body(self):
        for i, segment in enumerate(self.segments):
            if i > 0:
                dx = self.segments[i - 1][0] - segment[0]
                dy = self.segments[i - 1][1] - segment[1]
                dis = math.sqrt((dx ** 2) + (dy ** 2))
                new_proportional_dis = self.spacing / dis
                if new_proportional_dis < 1:
                    segment[0] = self.segments[i - 1][0] - dx * new_proportional_dis
                    segment[1] = self.segments[i - 1][1] - dy * new_proportional_dis

    def update(self, dt):
        distance = pp.game_math.distance(self.e['Game'].player.center, self.rect.center)
        if distance > 6:
            target = None
            # apply astar path if reasonable
            if distance >= 24:
                closest_space = self.e['Tilemap'].closest_space(self.rect.center)
                player_space = self.e['Tilemap'].closest_space(self.e['Game'].player.center)
                # create new path if no valid old path, rig is close to next point, or player moved
                if (not self.path) or (pp.game_math.distance(self.path[2], closest_space) < 1.5) or (pp.game_math.distance(self.path[-1], player_space) > 1.5):
                    self.path = list(self.e['Tilemap'].pathfinder.astar(closest_space, player_space))
                    if len(self.path) < 3:
                        self.path = None
                if self.path:
                    target = ((self.path[2][0] + 0.5) * self.e['Tilemap'].tile_size, (self.path[2][1] + 0.5) * self.e['Tilemap'].tile_size)
            if not target:
                target = (self.e['Game'].player.center[0], self.e['Game'].player.center[1])

            self.base_angle = math.atan2(target[1] - self.rect.center[1], target[0] - self.rect.center[0])
            self.angle = pp.utils.game_math.rotate_towards(self.angle, self.base_angle + math.cos(self.e['Window'].time * 5 + self.seed), dt * 10)
            movement = (math.cos(self.angle) * self.speed * dt, math.sin(self.angle) * self.speed * dt)
            self.physics_update(movement)
            self.time = self.e['Window'].time
        else:
            if self.e['Game'].player.damage(1):
                self.e['Game'].player.kb_stack.append([self.base_angle, 200])

        self.e['Game'].gm.apply_force(self.rect.center, 8, 8)

        self.segments[0] = list(self.rect.center)

        self.pull_body()

        # add info for aim assist
        if self.e['Settings'].aim_assist:
            player = self.e['Game'].player
            if pp.game_math.fast_range_check(player.center, self.center, player.weapon.max_range):
                angle = math.atan2(self.center[1] - player.center[1], self.center[0] - player.center[0])
                self.e['Machines'].machines_in_range.append((angle, len(self.e['Machines'].machines_in_range), self))

        if not self.health:
            return True

    def damage(self, amt):
        # killed if health drops to 0 from this damage
        killed = self.health - amt <= 0 < self.health

        self.health = max(0, self.health - amt)
        self.e['Game'].player.process_damage_applied(self, amt)
        for i in range(random.randint(1, 3)):
            anim = Animation('flash', (self.segments[0][0] + random.randint(-4, 4), self.segments[0][1] + random.randint(-4, 4)))
            anim.animation.update(random.random() * 0.3 + 0.3)
            anim.flip[0] = random.choice([True, False])
            self.e['EntityGroups'].add(anim, 'vfx')
        
        self.e['Game'].player.play_from('machine_hit', self.segments[0], volume=0.7)

        if killed:
            for j, segment in enumerate(self.segments):
                for i in range(6):
                    self.e['EntityGroups'].add(pp.vfx.Spark(segment, random.random() * math.pi * 2, size=(random.randint(5, 7), 1), speed=random.random() * 60 + 60, decay=random.random() * 1 + 1, color=random.choice([(254, 252, 211), (38, 27, 46)]), z=0), 'vfx')
                for i in range(random.randint(1, 3)):
                    anim = Animation('flash', (segment[0] + random.randint(-4, 4), segment[1] + random.randint(-4, 4)))
                    anim.animation.update(random.random() * 0.15 + (len(self.segments) - j) / len(self.segments) * 0.45)
                    anim.flip[0] = random.choice([True, False])
                    self.e['EntityGroups'].add(anim, 'vfx')
            for i in range(random.randint(2, 3)):
                self.e['EntityGroups'].add(Drop('scrap', self.segments[0]), 'entities')
            
            self.e['Game'].player.play_from('destroy', self.segments[0], volume=0.7)

            if self.e['State'].effect_active('collateral'):
                for i in range(random.randint(3, 4)):
                    angle = random.random() * math.pi * 2
                    self.e['EntityGroups'].add(Bullet('blue', self.segments[0], angle), 'entities')

    def renderz(self, offset=(0, 0), group='default'):
        antenna_r = pygame.transform.rotate(self.images['antenna'], -math.degrees(self.angle + math.pi / 2 + 1 + math.cos(self.time * 8) * 0.5))
        antenna_l = pygame.transform.rotate(self.images['antenna'], -math.degrees(self.angle + math.pi / 2 - 1 + math.cos(self.time * 7) * 0.5))
        shadow_img = self.e['Assets'].images['misc']['shadow_small']
        for img in [antenna_r, antenna_l]:
            self.e['Renderer'].blit(img, (self.segments[0][0] - offset[0] - img.get_width() // 2, self.segments[0][1] - offset[1] - img.get_height() // 2), group=group, z=self.z - 0.05)
        for i, segment in enumerate(self.segments):
            if i == 0:
                angle = self.angle
                src_img = self.images['head']
            else:
                ref_pos = self.segments[i - 1]
                angle = math.atan2(ref_pos[1] - segment[1], ref_pos[0] - segment[0])
                src_img = self.images['body']
            body = pygame.transform.rotate(src_img, -math.degrees(angle + math.pi / 2))
            left_angle_offset = math.cos(self.time * 20 + i * math.pi * 0.8) * 0.5
            right_angle_offset = math.cos(self.time * 20 + i * math.pi * 0.8 + 0.8) * 0.5
            leg_r = pygame.transform.rotate(self.images['leg_top'], -math.degrees(angle + math.pi / 2 + right_angle_offset))
            leg_l = pygame.transform.rotate(self.images['leg_top'], -math.degrees(angle + math.pi * 3 / 2 + left_angle_offset))
            self.e['Renderer'].blit(shadow_img, (segment[0] - offset[0] - shadow_img.get_width() // 2, segment[1] - offset[1] - shadow_img.get_height() // 2 + 4), group=group, z=-99)
            for j, img in enumerate([body, leg_r, leg_l]):
                self.e['Renderer'].blit(img, (segment[0] - offset[0] - img.get_width() // 2, segment[1] - offset[1] - img.get_height() // 2), group=group, z=self.z - i * 0.001 - j * 0.0001)
            leg_r_lower = pygame.transform.scale(self.images['leg_bottom'], (self.images['leg_bottom'].get_width(), self.images['leg_bottom'].get_height() * (1 - abs(right_angle_offset) * 1.3)))
            leg_l_lower = pygame.transform.scale(pygame.transform.flip(self.images['leg_bottom'], True, False), (self.images['leg_bottom'].get_width(), self.images['leg_bottom'].get_height() * (1 - abs(left_angle_offset) * 1.5)))
            lower_r_pos = pp.utils.game_math.advance(segment.copy(), angle + math.pi / 2 + right_angle_offset, self.leg_length)
            lower_l_pos = pp.utils.game_math.advance(segment.copy(), angle - math.pi / 2 + left_angle_offset, self.leg_length)
            self.e['Renderer'].blit(leg_r_lower, (lower_r_pos[0] - offset[0] - leg_r_lower.get_width() // 2, lower_r_pos[1] - offset[1] - leg_r_lower.get_height() // 2), group=group, z=self.z - i * 0.001 - 0.1)
            self.e['Renderer'].blit(leg_l_lower, (lower_l_pos[0] - offset[0] - leg_l_lower.get_width() // 2, lower_l_pos[1] - offset[1] - leg_l_lower.get_height() // 2), group=group, z=self.z - i * 0.001 - 0.1)

        tail_r = pygame.transform.rotate(self.images['tail'], -math.degrees(angle - math.pi / 2 + 0.4 + math.cos(self.time * 4) * 0.3))
        tail_l = pygame.transform.rotate(self.images['tail'], -math.degrees(angle - math.pi / 2 - 0.4 + math.cos(self.time * 3) * 0.3))
        for img in [tail_r, tail_l]:
            self.e['Renderer'].blit(img, (self.segments[-1][0] - offset[0] - img.get_width() // 2, self.segments[-1][1] - offset[1] - img.get_height() // 2), group=group, z=self.z - 0.05)
