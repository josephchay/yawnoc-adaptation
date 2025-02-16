import math
import random

import pygame

from . import pygpen as pp

from .physics_entity import PhysicsEntity
from .animation import Animation
from .weapon import Weapon

class Player(PhysicsEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_speed = 70

        self.weapon = Weapon('rifle', self)
        self.alt_weapon = None
        self.swap_cooldown = 0

        self.angle = 0

        self.roll_cooldown = 0
        self.roll_direction = 0
        self.roll_angle = 0

        self.kb_stack = []

        self.v_velocity = 0
        self.gravity = -300
        self.height = 0

        self.hurt = 0
        self.max_health = 5.2
        self.health = self.max_health

        self.hitbox = pygame.Rect(self.pos[0], self.pos[1] - 8, 9, 14)

        self.moved = False

        self.last_movement_flip = False

        self.friendly = True

        self.partner = [None, 0]

    @property
    def speed(self):
        return self.base_speed * (1.04 ** self.e['State'].owned_upgrades['swiftness'])

    @property
    def dead(self):
        return not self.health

    @property
    def rolling(self):
        return self.roll_direction != 0
    
    def reset(self):
        self.max_health = 5.2
        self.health = self.max_health
        self.alt_weapon = None
    
    def heal(self, amt):
        self.health = min(self.max_health, self.health + amt)
    
    def process_damage_applied(self, target, amt):
        if self.e['State'].effect_active('lifesteal'):
            self.health = min(self.health + amt * 0.03, self.max_health)
    
    def die(self):
        self.e['Transition'].transition()
        for i in range(50):
            self.e['EntityGroups'].add(pp.vfx.Spark(self.center, random.random() * math.pi * 2, size=(random.randint(5, 12), random.randint(1, 2)), speed=random.random() * 60 + 60, decay=random.random() * 2 + 0.5, color=random.choice([(254, 252, 211), (191, 60, 96)]), z=0), 'vfx')

    def play_from(self, sound, pos, volume=1.0):
        center = [self.e['Game'].camera.pos[0] + self.e['Game'].camera.size[0] / 2, self.e['Game'].camera.pos[1] + self.e['Game'].camera.size[1] / 2]
        angle = math.degrees(math.atan2(pos[1] - center[1], pos[0] - center[0]) + math.pi / 2)
        dis = pp.utils.game_math.distance(self.center, pos) / 5
        self.e['Sounds'].play(sound, angle=angle, distance=dis, volume=volume)
    
    def damage(self, damage):
        if ((not self.hurt) and (not self.e['State'].effect_active('invincibility'))) and self.health:
            self.e['Sounds'].play('player_hit', volume=0.5)
            self.health = max(0, self.health - damage)
            if not self.health:
                self.die()
            self.hurt = 1
            self.e['Game'].freeze_stack.append([0.1, 0.25])
            self.e['Game'].camera.screenshake = max(self.e['Game'].camera.screenshake, 0.25)
            return True

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)

        self.outline = (38, 27, 46) if (self.e['Settings'].setting('outline') == 'enabled') else None

        self.hurt = max(0, self.hurt - self.e['Window'].dt)

        if not self.partner[1]:
            self.partner[0] = None
        self.partner[1] = max(0, self.partner[1] - 1)

        self.v_velocity += self.e['Window'].dt * self.gravity
        height_min = -48 if self.e['Transition'].level_end else 0
        self.height = max(height_min, self.height + self.v_velocity * self.e['Window'].dt)
        if self.height <= height_min:
            if (self.v_velocity < -100) and (not self.e['Transition'].level_end):
                self.e['Sounds'].play('land', volume=0.7)
                anim = Animation('turn', (self.center[0] - 6, self.pos[1] + self.size[1]))
                self.e['EntityGroups'].add(anim, 'vfx')
                anim = Animation('turn', (self.center[0] + 6, self.pos[1] + self.size[1]))
                anim.flip[0] = True
                self.e['EntityGroups'].add(anim, 'vfx')
            self.v_velocity = 0

        self.opacity = min(255, 255 + self.height * 8)

        movement = [0, 0]
        if (not self.dead) and (not self.e['Transition'].level_end) and (not self.e['State'].title) and (not self.e['State'].ui_busy):
            self.e['Game'].gm.apply_force((self.center[0], self.pos[1] + self.size[1]), 4, 4)

            if self.e['Game'].controller_mode:
                movement = self.e['Controllers'].read_stick('move_x', 'move_y')
                movement[0] *= self.speed * self.e['Window'].dt
                movement[1] *= self.speed * self.e['Window'].dt
            else:
                if self.e['Input'].holding('right'):
                    movement[0] += self.speed * self.e['Window'].dt
                if self.e['Input'].holding('left'):
                    movement[0] -= self.speed * self.e['Window'].dt
                if self.e['Input'].holding('down'):
                    movement[1] += self.speed * self.e['Window'].dt
                if self.e['Input'].holding('up'):
                    movement[1] -= self.speed * self.e['Window'].dt

                # make diagonal movement proportional
                if (movement[0] and movement[1]):
                    movement[0] /= math.sqrt(2)
                    movement[1] /= math.sqrt(2)

            self.weapon.update(self.e['Window'].dt)
            if self.alt_weapon:
                self.alt_weapon.update(self.e['Window'].dt)
            self.swap_cooldown = max(0, self.swap_cooldown - self.e['Window'].dt)

            if (self.e['Input'].pressed('swap_weapon') or (self.e['Game'].controller_mode and self.e['Controllers'].pressed('swap'))) and (not self.swap_cooldown) and self.alt_weapon:
                self.weapon, self.alt_weapon = self.alt_weapon, self.weapon
                self.swap_cooldown = 0.5
                self.e['HUD'].swap_offset = 16

            if (self.e['Input'].holding('shoot') or (self.e['Game'].controller_mode and self.e['Controllers'].holding('primary'))) and (not self.rolling):
                self.weapon.attempt_fire()

            if (self.e['Input'].holding('secondary') or (self.e['Game'].controller_mode and self.e['Controllers'].holding('secondary'))) and (not self.rolling):
                if not self.weapon.attempt_secondary():
                    if self.e['Input'].pressed('secondary') or (self.e['Game'].controller_mode and self.e['Controllers'].pressed('secondary')):
                        self.e['Sounds'].play('cooldown', volume=1.0)

            self.roll_cooldown = max(0, self.roll_cooldown - self.e['Window'].dt)
            if self.e['Input'].pressed('dodge') or (self.e['Game'].controller_mode and self.e['Controllers'].pressed('dodge')):
                if not self.roll_cooldown:
                    self.e['Sounds'].play('roll', volume=0.5)
                    self.roll_cooldown = 1
                    self.roll_direction = -1 if self.flip[0] else 1
                    anim_dir = 1
                    if movement[0] > 0:
                        self.roll_direction = 1
                    if movement[0] < 0:
                        self.roll_direction = -1
                        anim_dir = -1
                    if not movement[0]:
                        anim_dir = 0
                    
                    if (anim_dir == 1) or (not anim_dir):
                        anim = Animation('turn', (self.center[0] - 6, self.pos[1] + self.size[1]))
                        self.e['EntityGroups'].add(anim, 'vfx')
                    if (anim_dir == -1) or (not anim_dir):
                        anim = Animation('turn', (self.center[0] + 6, self.pos[1] + self.size[1]))
                        anim.flip[0] = True
                        self.e['EntityGroups'].add(anim, 'vfx')

                    self.kb_stack.append([math.atan2(movement[1], movement[0]), self.speed * 3])

                    if self.partner[0]:
                        self.partner[0].kb_stack.append([math.atan2(movement[1], movement[0]), self.speed * 3])
                        self.partner[0].roll_direction = self.roll_direction
                        self.partner[0].roll_angle = self.roll_angle

        for kb in self.kb_stack[::-1]:
            movement[0] += math.cos(kb[0]) * kb[1] * self.e['Window'].dt
            movement[1] += math.sin(kb[0]) * kb[1] * self.e['Window'].dt
            kb[1] = max(0, kb[1] - self.e['Window'].dt * 500)
            if not kb[1]:
                self.kb_stack.remove(kb)

        if self.roll_direction:
            self.roll_angle += self.roll_direction * self.e['Window'].dt * 20
            if (self.roll_angle > math.pi * 2) or (self.roll_angle < -math.pi * 2):
                self.roll_angle = 0
                self.roll_direction = 0
            self.rotation = -math.degrees(self.roll_angle)
            self.scale = [1, 0.5]
            self.config['offset'] = [-3, -5]
        else:
            self.scale = [1, 1]
            self.config['offset'] = [-3, -14]

        if movement[0] > 0:
            if self.flip[0]:
                self.set_action('run_reverse')
            else:
                self.set_action('run')
            if not self.last_movement_flip:
                anim = Animation('turn', (self.center[0] - 6, self.pos[1] + self.size[1]))
                self.e['EntityGroups'].add(anim, 'vfx')
            self.last_movement_flip = True
        elif movement[0] < 0:
            if self.flip[0]:
                self.set_action('run')
            else:
                self.set_action('run_reverse')
            if self.last_movement_flip:
                anim = Animation('turn', (self.center[0] + 6, self.pos[1] + self.size[1]))
                anim.flip[0] = True
                self.e['EntityGroups'].add(anim, 'vfx')
            self.last_movement_flip = False
        elif movement[1] == 0:
            self.set_action('idle')
        else:
            self.set_action('run')
        if self.height:
            self.set_action('jump')

        if sum(movement):
            self.moved = True

        self.physics_update(movement)

        self.z = self.pos[1] / self.e['Tilemap'].tile_size

        mouse_offset = pygame.Vector2(self.e['Game'].mpos) + self.e['Game'].camera.pos - self.gun_center
        self.angle = math.atan2(mouse_offset.y, mouse_offset.x)

        self.hitbox = pygame.Rect(self.pos[0], self.pos[1] - 8, 9, 14)
    
    @property
    def gun_center(self):
        return (self.center[0], self.pos[1] - 4)
    
    @property
    def img(self):
        if self.e['Settings'].setting('pink_player') == 'enabled':
            img = super().img
            return pygame.mask.from_surface(img).to_surface(setcolor=(255, 0, 255), unsetcolor=(0, 0, 0, 0))
        return super().img

    def renderz(self, *args, **kwargs):
        if not self.dead:
            if ((not self.hurt) and (not self.e['State'].effect_active('invincibility'))) or (random.random() < 0.7):
                super().renderz(*args, offset=(self.e['Game'].camera[0], self.e['Game'].camera[1] + self.height), group='default')

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

            if not self.e['Transition'].level_end:
                shadow_img = self.e['Assets'].images['misc']['shadow']
                self.e['Renderer'].blit(shadow_img, (self.center[0] - shadow_img.get_width() // 2 - self.e['Game'].camera[0], self.pos[1] + self.size[1] - shadow_img.get_height() // 2 - self.e['Game'].camera[1]), z=-99998)