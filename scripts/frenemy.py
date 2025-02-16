import time
import math
import random

import pygame

from . import pygpen as pp

from .physics_entity import PhysicsEntity
from .weapon import Weapon
from .animation import Animation
from .pygpen.vfx import Particle

BOSS_NAMES = {
    'jim': 'Jim'
}

DIALOGUE = {
    'jim': ['...', 'Wha-', 'What just happened?']
}

STATS = {
    'jim': {
        'friend_health': 5.5,
        'enemy_health': 40,
        'weapon': 'pistol',
    }
}

class Frenemy(PhysicsEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.weapon = Weapon(STATS[self.type]['weapon'], self)

        self.friendly = False
        self.revived = False
        self.alerted = False

        self.base_speed = 50
        self.angle = 0

        self.health = self.max_health
        self.z = 0
        self.height = 0

        self.set_action('idle_shadow')

        self.path = None

        self.range = 12 * 10

        self.dead = False
        self.hurt = 0
        self.fallen_timer = 0

        self.kb_stack = []

        self.roll_direction = 0
        self.roll_angle = 0
        self.v_velocity = 0
        self.gravity = -300

        self.base_offset = self.config['offset'].copy()

    @property
    def weight(self):
        return 1 if self.friendly else 3

    @property
    def max_health(self):
        if self.friendly:
            return STATS[self.type]['friend_health'] + (self.e['Game'].player.max_health - 5)
        return STATS[self.type]['enemy_health']

    @property
    def name(self):
        return BOSS_NAMES[self.type]
    
    @property
    def rolling(self):
        return self.roll_direction != 0

    def destroy(self):
        self.dead = True

    def damage(self, damage):
        if self.friendly:
            if self.hurt or self.e['State'].effect_active('invincibility'):
                return False
        self.e['Game'].player.process_damage_applied(self, damage)
        if self.health and (damage >= self.health):
            self.e['Game'].player.play_from('npc_death', self.center, volume=0.6)
        self.health = max(0, self.health - damage)
        self.hurt = 0.3
        for i in range(random.randint(1, 3)):
            anim = Animation('flash', (self.center[0] + random.randint(-6, 6), self.center[1] + random.randint(-9, 6)))
            anim.animation.update(random.random() * 0.3 + 0.3)
            anim.flip[0] = random.choice([True, False])
            self.e['EntityGroups'].add(anim, 'vfx')
        self.e['Game'].player.play_from('machine_hit', self.center, volume=0.7)
        return True
    
    @property
    def action_suffix(self):
        if self.friendly:
            return ''
        return '_shadow'

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)

        self.outline = (38, 27, 46) if ((self.e['Settings'].setting('outline') == 'enabled') and self.friendly) else None

        self.hurt = max(0, self.hurt - self.e['Window'].dt)

        distance = pp.game_math.distance(self.e['Game'].player.center, self.rect.center)

        if self.friendly:
            self.e['Game'].player.partner = [self, 1]

        if not self.friendly:
            self.e['HUD'].boss = self

            if (not self.e['Machines'].active_enemies_remaining) and (self.fallen_timer > 2.5):
                if distance < 24:
                    self.friendly = True
                    for i in range(20):
                        color = random.choice([(100, 97, 139), (121, 132, 157), (163, 179, 182)])
                        angle = random.random() * math.pi * 2
                        speed = random.random() * 40 + 10
                        p = Particle((self.center[0] + random.randint(-6, 6), self.center[1] + random.randint(-4, 4)), 'basep', (math.cos(angle) * speed, math.sin(angle) * speed), decay_rate=0.5, advance=0.2 + 0.4 * random.random(), colors={(255, 255, 255): color}, z=self.z + 0.005, behavior='smoke')
                        self.e['EntityGroups'].add(p, 'particles')
                    self.health = self.max_health
                    self.e['State'].dialogue = [self, DIALOGUE[self.type].copy()]
                    self.kb_stack = []
                    self.revived = True
                else:
                    self.e['HUD'].guide_target = tuple(self.center)

        if (not self.e['State'].ui_busy) and self.revived and (not self.alerted):
                self.e['HUD'].new_team_alert(self)
                self.alerted = True

        movement = [0, 0]

        if self.health:
            self.v_velocity += self.e['Window'].dt * self.gravity
            height_min = -48 if self.e['Transition'].level_end else 0
            self.height = max(height_min, self.height + self.v_velocity * self.e['Window'].dt)
            if self.height <= height_min:
                if (self.v_velocity < -100) and (not self.e['Transition'].level_end):
                    anim = Animation('turn', (self.center[0] - 6, self.pos[1] + self.size[1]))
                    self.e['EntityGroups'].add(anim, 'vfx')
                    anim = Animation('turn', (self.center[0] + 6, self.pos[1] + self.size[1]))
                    anim.flip[0] = True
                    self.e['EntityGroups'].add(anim, 'vfx')
                self.height = height_min
                self.v_velocity = 0

            self.opacity = min(255, 255 + self.height * 8)

            if self.roll_direction:
                self.roll_angle += self.roll_direction * self.e['Window'].dt * 20
                if (self.roll_angle > math.pi * 2) or (self.roll_angle < -math.pi * 2):
                    self.roll_angle = 0
                    self.roll_direction = 0
                self.rotation = -math.degrees(self.roll_angle)
                self.scale = [1, 0.5]
                self.config['offset'] = [self.base_offset[0], self.base_offset[1] * 0.25]
            else:
                self.scale = [1, 1]
                self.config['offset'] = self.base_offset

            if not self.friendly:
                target = None
                closest_space = self.e['Tilemap'].closest_space(self.rect.center)
                player_space = self.e['Tilemap'].closest_space(self.e['Game'].player.center)
                line_of_sight = not self.e['Tilemap'].physics_gridline(closest_space, player_space, include_gaps=False)
                # apply astar path if reasonable
                if (distance >= self.range) or (not line_of_sight):
                    # create new path if no valid old path, entity is close to next point, or player moved
                    if (not self.path) or (pp.game_math.distance(self.path[2], closest_space) < 1.5) or (pp.game_math.distance(self.path[-1], player_space) > 1.5):
                        self.path = list(self.e['Tilemap'].pathfinder.astar(closest_space, player_space))
                        if len(self.path) < 3:
                            self.path = None
                    if self.path:
                        target = ((self.path[2][0] + 0.5) * self.e['Tilemap'].tile_size, (self.path[2][1] + 0.5) * self.e['Tilemap'].tile_size)
                        angle = math.atan2(target[1] - self.rect.center[1], target[0] - self.rect.center[0])
                    else:
                        target = self.e['Game'].player.center
                        angle = math.atan2(target[1] - self.rect.center[1], target[0] - self.rect.center[0])

                    movement = [math.cos(angle) * self.base_speed * self.e['Window'].dt, math.sin(angle) * self.base_speed * self.e['Window'].dt]
                
                elif distance < self.range - 12 * 3:
                    target = self.e['Game'].player.center
                    angle = math.atan2(target[1] - self.rect.center[1], target[0] - self.rect.center[0]) + math.pi
                    movement = [math.cos(angle) * self.base_speed * self.e['Window'].dt, math.sin(angle) * self.base_speed * self.e['Window'].dt]
            
            elif (distance > 14) and (not self.e['State'].ui_busy):
                target = self.e['Game'].player.center
                angle = math.atan2(target[1] - self.rect.center[1], target[0] - self.rect.center[0])
                speed = self.e['Game'].player.speed + max(0, (distance - 16) * 4)
                movement = [math.cos(angle) * speed * self.e['Window'].dt, math.sin(angle) * speed * self.e['Window'].dt]
                
                # handle flip when it doesn't have a gun
                if self.revived:
                    if movement[0] > 0:
                        self.flip[0] = False
                    elif movement[0] < 0:
                        self.flip[0] = True

            for kb in self.kb_stack[::-1]:
                movement[0] += math.cos(kb[0]) * kb[1] * self.e['Window'].dt / self.weight
                movement[1] += math.sin(kb[0]) * kb[1] * self.e['Window'].dt / self.weight
                kb[1] = max(0, kb[1] - self.e['Window'].dt * 500)
                if not kb[1]:
                    self.kb_stack.remove(kb)

            if movement != [0, 0]:
                if movement[0] > 0:
                    if self.flip[0]:
                        self.set_action(f'run_reverse{self.action_suffix}')
                    else:
                        self.set_action(f'run{self.action_suffix}')
                elif movement[0] < 0:
                    if self.flip[0]:
                        self.set_action(f'run{self.action_suffix}')
                    else:
                        self.set_action(f'run_reverse{self.action_suffix}')
                else:
                    self.set_action(f'run{self.action_suffix}')
            else:
                self.set_action(f'idle{self.action_suffix}')

            self.weapon.update(self.e['Window'].dt)
            if not self.friendly:
                if line_of_sight and (time.time() - self.e['Machines'].wave_start > 2):
                    self.weapon.attempt_fire()

                self.physics_update(movement)
                self.angle = math.atan2(self.e['Game'].player.pos[1] - self.pos[1], self.e['Game'].player.pos[0] - self.pos[0])
            else:
                self.pos[0] += movement[0]
                self.pos[1] += movement[1]
                mouse_offset = pygame.Vector2(self.e['Game'].mpos) + self.e['Game'].camera.pos - self.gun_center
                self.angle = math.atan2(mouse_offset.y, mouse_offset.x)
                if (self.e['Input'].holding('shoot') or (self.e['Game'].controller_mode and self.e['Controllers'].holding('primary'))) and (not self.rolling) and self.weapon and (not self.revived) and (not self.e['State'].ui_busy) and (not self.e['Transition'].level_end) and (not self.e['Game'].player.dead):
                    self.weapon.attempt_fire(damage_scale=0.5)
            
        else:
            self.set_action(f'fall{self.action_suffix}')
            self.fallen_timer += self.e['Window'].dt

        if self.height and ('fall' not in self.action):
            self.set_action(f'jump{self.action_suffix}')

        self.z = self.pos[1] / self.e['Tilemap'].tile_size

        # add info for aim assist
        if (not self.friendly) and self.health and self.e['Settings'].aim_assist:
            player = self.e['Game'].player
            if pp.game_math.fast_range_check(player.center, self.center, player.weapon.max_range):
                angle = math.atan2(self.center[1] - player.center[1], self.center[0] - player.center[0])
                self.e['Machines'].machines_in_range.append((angle, len(self.e['Machines'].machines_in_range), self))

        return self.dead

    @property
    def gun_center(self):
        return (self.center[0], self.pos[1] + 1)

    def renderz(self, *args, **kwargs):
        super().renderz(*args, offset=(self.e['Game'].camera[0], self.e['Game'].camera[1] + self.height), group='default')

        if self.health and (not self.revived):
            weapon_img = self.weapon.img
            if abs((self.angle + math.pi) % (math.pi * 2) - math.pi) > math.pi / 2:
                weapon_img = pygame.transform.flip(weapon_img, False, True)
                self.flip[0] = True
            else:
                self.flip[0] = False
            
            if not self.rolling:
                weapon_img = pygame.transform.rotate(weapon_img, -math.degrees(self.angle))
                weapon_img.set_alpha(self.opacity)
                pos = (self.gun_center[0] - weapon_img.get_width() // 2 - self.e['Game'].camera[0], self.gun_center[1] - weapon_img.get_height() // 2 - self.e['Game'].camera[1] - self.height)
                self.e['Renderer'].blit(weapon_img, pos, z=self.z + 0.01)
        
        elif self.animation.finished:
            for i in range(5):
                angle = math.pi * 2 * i / 5
                star_img = self.e['Assets'].images['misc']['star']
                t = time.time() * 2.1
                pos = (self.center[0] + math.cos(angle + t) * 6 - star_img.get_width() // 2 - self.e['Game'].camera[0], self.pos[1] - 2 + math.sin(angle + t) * 6 - star_img.get_height() // 2 - self.e['Game'].camera[1])
                z = self.z + 0.01 if math.sin(angle + t) > 0 else self.z - 0.01
                self.e['Renderer'].blit(star_img, pos, z=z)
    
        shadow_img = self.e['Assets'].images['misc']['shadow']
        self.e['Renderer'].blit(shadow_img, (self.center[0] - shadow_img.get_width() // 2 - self.e['Game'].camera[0], self.pos[1] + self.size[1] - shadow_img.get_height() // 2 - self.e['Game'].camera[1]), z=-99998)