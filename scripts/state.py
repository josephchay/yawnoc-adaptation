import math
import random

import pygame

from . import pygpen as pp

from .debris import Debris, AbilityDrop
from .drops import Drop
from .bullet import Bullet
from .weapon import Weapon, WEAPON_STATS, ENCHANTS
from .rig import CentipedeRig
from .slash import Slash
from .util import nice_round, roman_numeral

SEASON_STATS = {
    'summer': {
        'pause': 1.0,
        'count': 1.0,
    },
    'fall': {
        'pause': 1.5,
        'count': 0.5,
    },
    'winter': {
        'pause': 1.5,
        'count': 0.5,
    }
}

SHOP_UPGRADES = ['extra_rounds', 'heart', 'potion', 'scoped_weapons', 'swiftness', 'winged_bullets', 'stopwatch', 'frost_touch', 'ricochet']

UPGRADE_INFO = {
    'extra_rounds': {
        'name': 'Extra Rounds',
        'template': 'Increases weapon rate of fire by [STAT]%.',
        'stat_pattern': 'exponential',
        'stat_rate': 0.08,
        'base_price': 35,
    },
    'heart': {
        'name': 'Heart',
        'template': 'Increases max health by [STAT].',
        'stat_pattern': 'linear',
        'stat_rate': 1,
        'base_price': 50,
    },
    'potion': {
        'name': 'Potion',
        'desc': 'Heals 2 + 20% missing health.',
        'stat_pattern': 'linear',
        'stat_rate': 1,
        'base_price': 25,
    },
    'scoped_weapons': {
        'name': 'Scoped Weapons',
        'template': 'Increases weapon range by [STAT]%.',
        'stat_pattern': 'exponential',
        'stat_rate': 0.1,
        'base_price': 35,
    },
    'swiftness': {
        'name': 'Swiftness',
        'template': 'Increases movement speed by [STAT]%.',
        'stat_pattern': 'exponential',
        'stat_rate': 0.04,
        'base_price': 20,
    },
    'winged_bullets': {
        'name': 'Winged Bullets',
        'template': 'Increases bullet velocity by [STAT]%.',
        'stat_pattern': 'exponential',
        'stat_rate': 0.15,
        'base_price': 18,
    },
    'stopwatch': {
        'name': 'Stopwatch',
        'template': 'Reduces secondary cooldown by [STAT]%.',
        'stat_pattern': 'inverse_exponential',
        'stat_rate': 0.14,
        'base_price': 32,
    },
    'frost_touch': {
        'name': 'Frost Touch',
        'template': '[STAT]% chance to freeze enemies.',
        'stat_pattern': 'inverse_exponential',
        'stat_rate': 0.06,
        'base_price': 40,
    },
    'ricochet': {
        'name': 'Ricochet',
        'template': 'Increase friendly bullet ricochet max by [STAT].',
        'stat_pattern': 'linear',
        'stat_rate': 1,
        'base_price': 100,
    },
    'next': {
        'name': 'Next Wave',
        'desc': '',
        'base_price': 0,
    }
}

def generate_description(upgrade_id, level):
    info = UPGRADE_INFO[upgrade_id]
    if 'desc' in info:
        return info['desc']
    
    stat_str = ''
    if info['stat_pattern'] == 'exponential':
        stat_str = nice_round(((1 + info['stat_rate']) ** level - 1) * 100)
    elif info['stat_pattern'] == 'inverse_exponential':
        stat_str = nice_round((1 - (1 - info['stat_rate']) ** level) * 100)
    else:
        # linear addition case
        stat_str = nice_round(info['stat_rate'] * level)
    return info['template'].replace('[STAT]', stat_str)

UPGRADE_INFO.update(WEAPON_STATS)

EFFECTS = {
    'invincibility': 'Invincibility',
    'collateral': 'Collateral Damage',
    'double_barrel': 'Double Barrel',
    'lifesteal': 'Lifesteal',
    'freeze': 'Freeze',
    'extra_rounds': 'Extra Rounds'
}

def calc_price(base, stacks):
    return int(base * (1.35 ** stacks))

class Interactable(pp.Element):
    def __init__(self, category, subtype, pos, price=0):
        super().__init__()

        self.pos = tuple(pos)
        self.category = category
        self.type = subtype
        self.price = price
        
        self.dis = 99999
    
    def render(self):
        if (pp.game_math.distance(self.pos, self.e['Game'].player.center) < 260) and (self.category == 'next'):
            self.e['HUD'].guide_target = tuple(self.pos)

        shadow_img = self.e['Assets'].images['misc']['shadow_medium']
        self.dis = pp.utils.game_math.distance(self.pos, self.e['Game'].player.center)
        if self.category == 'next':
            img = self.e['Assets'].images['upgrades']['next']
        elif self.category == 'shop':
            img = self.e['Assets'].images['upgrades'][self.type]
        elif self.category == 'weapon':
            img = self.e['Assets'].images['weapons'][f'{self.type}_icon']
        if self.price:
            price_text = f'{self.price:,}'
            text_width = self.e['Text']['small_font'].width(price_text)
            scrap_width = self.e['Assets'].images['misc']['scrap'].get_width()
            price_width = text_width + scrap_width + 2
            self.e['Text']['small_font'].renderzb(f'{self.price:,}', (self.pos[0] - self.e['Game'].camera[0] - price_width / 2 + scrap_width + 2, self.pos[1] - self.e['Game'].camera[1] - 34 + math.cos(self.e['Window'].time * 1.2 + 0.1 * self.pos[0]) * 4.5), color=(254, 252, 211), bgcolor=(38, 27, 46), z=300)
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['scrap'], (self.pos[0] - self.e['Game'].camera[0] - price_width / 2, self.pos[1] - self.e['Game'].camera[1] - 35 + math.cos(self.e['Window'].time * 1.2 + 0.1 * self.pos[0]) * 4.5), group='default', z=300)
        self.e['Renderer'].blit(img, (self.pos[0] - self.e['Game'].camera[0] - img.get_width() // 2, self.pos[1] - self.e['Game'].camera[1] - img.get_height() // 2 - 16 + math.cos(self.e['Window'].time * 1.2 + 0.1 * self.pos[0]) * 4.5), group='default', z=self.pos[1] / self.e['Tilemap'].tile_size)
        self.e['Renderer'].blit(shadow_img, (self.pos[0] - self.e['Game'].camera[0] - shadow_img.get_width() // 2, self.pos[1] - self.e['Game'].camera[1] - shadow_img.get_height() // 2 + 3), group='default', z=-20)

class State(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        self.reset()

        save_file = pp.utils.io.read_json('save/save.json')
        self.record = save_file['best_score']
        self.weapon_enchants = save_file['weapon_enchants']

        self.pointer_anim = self.e['EntityDB']['misc'].animations['pointer'].copy()
        self.popup_pointer_anim = self.e['EntityDB']['misc'].animations['pointer'].copy()
    
    def save(self):
        save_data = {
            'best_score': self.record,
            'weapon_enchants': self.weapon_enchants,
        }
        pp.utils.io.write_json('save/save.json', save_data)

    @property
    def difficulty_status(self):
        return {
            'bullet_speed': 110 + self.difficulty / 9.5,
            'pause': SEASON_STATS[self.season]['pause'] * max(2, 5 - self.difficulty / 200),
            'count': SEASON_STATS[self.season]['count'],
        }

    def reset(self):
        self.wave = 0
        self.score = 0
        self.scrap = 0
        self.shopping = 0
        self.shop_upgrades = [None] * 3
        self.owned_upgrades = {upgrade: 0 for upgrade in SHOP_UPGRADES}
        self.notifications = []
        self.dialogue = [None, []]
        self.dialogue_state = {'progress': 0, 'ui_offset': 60}
        self.closest_entity = [None, 99999]
        self.difficulty = 0
        self.effects = {effect: [0, 0.01] for effect in EFFECTS}
        self.interactables = []
        self.enchanting = False
        self.enchanting_offset = 200
        self.enchanting_selection_index = 0
        self.enchant_anim_progress = 0
        self.enchant_anim_offset = 0
        if self.e['Game'].player:
            self.e['Game'].player.reset()
        # text, offset, callback, selection_i
        self.popup = [None, 200, None, 0]
        for group in ['enemies', 'frenemies', 'vfx']:
            self.e['EntityGroups'].groups[group] = []
        self.clear_map()

    @property
    def ui_busy(self):
        return self.e['State'].dialogue[0] or self.enchanting or self.title or self.e['PauseMenu'].paused
    
    @property
    def inv_enchanting_offset(self):
        return 200 - self.enchanting_offset
    
    @property
    def left_inv_offset(self):
        if self.inv_enchanting_offset:
            return self.inv_enchanting_offset
        elif self.e['PauseMenu'].pause_offset != 200:
            return 200 - self.e['PauseMenu'].pause_offset
        return 0
    
    @property
    def right_inv_offset(self):
        return self.left_inv_offset

    @property
    def season(self):
        wave = self.wave
        # new areas start with shopping area
        if self.shopping > 1:
            wave += 1

        if wave <= 10:
            return 'summer'
        elif wave <= 20:
            return 'fall'
        else:
            return 'winter'

    def clear_map(self):
        if 'enemies' in self.e['EntityGroups'].groups:
            for entity in self.e['EntityGroups'].groups['enemies']:
                if type(entity) == CentipedeRig:
                    entity.damage(entity.health)
        if 'entities' in self.e['EntityGroups'].groups:
            for entity in list(self.e['EntityGroups'].groups['entities']):
                if entity.type != 'player':
                    self.e['EntityGroups'].groups['entities'].remove(entity)
        if 'frenemies' in self.e['EntityGroups'].groups:
            for frenemy in list(self.e['EntityGroups'].groups['frenemies']):
                if not frenemy.friendly:
                    self.e['EntityGroups'].groups['frenemies'].remove(frenemy)
                else:
                    frenemy.revived = False
        if self.e['Game'].player:
            if self.e['Game'].player.weapon:
                self.e['Game'].player.weapon.reset()
            if self.e['Game'].player.alt_weapon:
                self.e['Game'].player.alt_weapon.reset()
        self.interactables = []

    def load_title(self):
        self.title = True
        self.e['Tilemap'].load_map('fortress')
        self.e['Music'].fadeout(0.5)
        self.e['Sounds'].sounds['ambience'].set_volume(self.e['Settings'].sfx_volume * 0.6)
        self.e['Menus'].submenu = 'title'

    def effect_active(self, effect_id):
        return self.effects[effect_id][0]

    def add_effect(self, effect_id, duration):
        if effect_id == 'freeze':
            self.e['Sounds'].play('long_freeze', volume=1.0)
        if duration > self.effects[effect_id][0]:
            self.effects[effect_id] = [duration, duration]
        self.notify(f'+{EFFECTS[effect_id]}', font='small_font')

    def notify(self, text, font='large_font'):
        self.notifications.append([text, self.e['Game'].display.get_height(), 3, font])

    def shop(self):
        if not self.shopping:
            self.shopping = 1
        self.e['Transition'].end_level(self.shop_land)

    def load_area(self, area_id):
        self.clear_map()

        self.e['Tilemap'].load_map(area_id)

        if self.wave or (not self.e['Tilemap'].respawn):
            self.e['Game'].player.pos = list(self.e['Tilemap'].spawn)
            self.e['Game'].player.height = 200
        else:
            self.e['Game'].player.pos = list(self.e['Tilemap'].respawn)
            self.e['Game'].player.height = 0

        if self.e['Game'].player.partner[0]:
            self.e['Game'].player.partner[0].pos = [self.e['Game'].player.pos[0] + 3, self.e['Game'].player.pos[0] - 4]
            self.e['Game'].player.partner[0].height = self.e['Game'].player.height
            self.e['Game'].player.partner[0].health = self.e['Game'].player.partner[0].max_health

        self.e['Machines'].minimap = self.e['Tilemap'].minimap_base.copy()
        self.e['Machines'].minimap.set_alpha(180)

    def shop_land(self):
        self.shopping = 2

        if self.season == 'fall':
            self.e['Music'].play('fall_shop', start=self.e['Window'].time, fadein=2.5)
        else:
            self.e['Music'].play('summer_shop', start=self.e['Window'].time, fadein=2.5)
        self.load_area(f'{self.e["State"].season}_transition')

        self.notify('Buy Phase')
        self.e['Sounds'].play('shop', volume=0.4)
        
        if self.wave > self.record:
            self.record = self.wave
            self.save()

        for shop_pos in self.e['Tilemap'].shops:
            item = random.choice(SHOP_UPGRADES)
            if random.random() < 0.1:
                item = 'potion'
            self.interactables.append(Interactable('shop', item, (shop_pos[0] + self.e['Tilemap'].tile_size * 0.5, shop_pos[1] + self.e['Tilemap'].tile_size * 0.5), calc_price(UPGRADE_INFO[item]['base_price'], self.owned_upgrades[item])))
        for shop_pos in self.e['Tilemap'].weapon_shops:
            weapon = random.choice(list(WEAPON_STATS.keys()))
            self.interactables.append(Interactable('weapon', weapon, (shop_pos[0] + self.e['Tilemap'].tile_size * 0.5, shop_pos[1] + self.e['Tilemap'].tile_size * 0.5), UPGRADE_INFO[weapon]['base_price']))
        
        self.interactables.append(Interactable('next', 'next', self.e['Tilemap'].exit))

    def end_shopping(self):
        self.shopping = 0
        self.e['Transition'].end_level(self.e['Machines'].new_wave)

    def update(self):
        if not (self.shopping or self.ui_busy):
            self.difficulty += self.e['Window'].dt

        for effect in self.effects:
            self.effects[effect][0] = max(0, self.effects[effect][0] - self.e['Window'].dt)
            if not self.effects[effect][0]:
                self.effects[effect][1] = 0.01

        for notification in self.notifications[::-1]:
            if notification[2] >= 0:
                notification[1] += (60 - notification[1]) * 3 * self.e['Window'].dt
            else:
                notification[1] += (-80 - notification[1]) * 3 * self.e['Window'].dt
            notification[2] -= self.e['Window'].dt
            if notification[2] < -2:
                self.notifications.remove(notification)

    def render_ability_cooldown(self, ability, pos, z=9999, group='default'):
        if self.e['Game'].player.weapon and (WEAPON_STATS[self.e['Game'].player.weapon.type]['primary'] == ability):
            cooldown_ratio = self.e['Game'].player.weapon.shoot_cooldown[0] / self.e['Game'].player.weapon.shoot_cooldown[1]
        else:
            cooldown_ratio = self.e['Game'].player.weapon.secondary_cooldown[0] / self.e['Game'].player.weapon.secondary_cooldown[1]
        img = self.e['Assets'].images['upgrades'][f'{ability}_b'].copy()
        if not cooldown_ratio:
            self.e['Renderer'].blit(img, pos, z=z, group=group)
        else:
            img.set_alpha(80)
            self.e['Renderer'].blit(img, pos, z=z, group=group)
            img.blit(pygame.Surface((img.get_width(), int((cooldown_ratio * 0.75 + 0.125) * img.get_height()))), (0, 0))
            self.e['Renderer'].blit(img, pos, z=z, group=group)
            self.e['Renderer'].blit(self.e['Assets'].images['upgrades']['frame'], pos, z=z, group=group)

    def strip_enchant_callback(self, response):
        if response:
            self.e['Game'].player.weapon.strip()
            self.e['Sounds'].play('strip_enchant', volume=1.0)
        self.e['Sounds'].play('tap')

    @property
    def interacted(self):
        return self.e['Input'].pressed('interact') or (self.e['Game'].controller_mode and self.e['Controllers'].pressed('interact'))
    
    def render_weapon_enchants(self, weapon, offset=(0, 0)):
        if len(weapon.enchant_list):
            for i, enchant in enumerate(weapon.enchant_list):
                self.e['Text']['small_font'].renderzb(f'{ENCHANTS[enchant[1]]["name"]} {roman_numeral(int(math.ceil(enchant[2] * enchant[0])))}', (4 - offset[0], 62 + 26 * i - offset[1]), color=(191, 60, 96), bgcolor=(38, 27, 46), z=9998, group='ui')
                self.e['Text']['small_font'].renderzb(ENCHANTS[enchant[1]]['text'].replace('<stat>', str(nice_round(weapon.enchant_stat(enchant[1]) * 100, 1))), (4 - offset[0], 72 + 26 * i - offset[1]), color=(163, 179, 182), bgcolor=(38, 27, 46), z=9998, group='ui')
        else:
            self.e['Text']['small_font'].renderzb('No active enchantments...', (4 - offset[0], 62 - offset[1]), color=(121, 132, 157), bgcolor=(38, 27, 46), z=9998, group='ui')

    def render(self):
        if self.shopping > 1:
            nearby_item = None

            for interactable in self.interactables:
                interactable.render()
                if interactable.dis < 12:
                    nearby_item = interactable

            if not self.ui_busy:
                if nearby_item:
                    self.e['Text']['small_font'].renderzb(UPGRADE_INFO[nearby_item.type]['name'], (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width(UPGRADE_INFO[nearby_item.type]['name']) / 2, 150 + math.cos(self.e['Window'].time * 2) * 2.5), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                    upgrade_desc = generate_description(nearby_item.type, 1)
                    self.e['Text']['small_font'].renderzb(upgrade_desc, (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width(upgrade_desc) / 2, 166 + math.cos(self.e['Window'].time * 1.7) * 2.5), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                    if nearby_item.category == 'next':
                        self.e['Text']['small_font'].renderzb('to proceed', (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width('to proceed') / 2 + 6, 182), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                        self.e['Renderer'].blit(self.e['Assets'].images['misc']['e'], (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width('to proceed') / 2 - 7, 179), group='ui', z=9998)
                        if self.interacted:
                            self.e['Sounds'].play('tap')
                            for j in range(25):
                                self.e['EntityGroups'].add(pp.vfx.Spark((nearby_item.pos[0], nearby_item.pos[1] - 16 + math.cos(self.e['Window'].time * 1.2 + 0.1 * nearby_item.pos[0]) * 4.5), random.random() * math.pi * 2, size=(random.randint(6, 10), random.randint(1, 2)), speed=random.random() * 60 + 60, decay=random.random() * 4 + 2, color=(254, 252, 211), z=300), 'vfx')
                            self.end_shopping()
                    elif nearby_item.price <= self.scrap:
                        self.e['Text']['small_font'].renderzb('to buy', (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width('to buy') / 2 + 6, 182), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                        self.e['Renderer'].blit(self.e['Assets'].images['misc']['e'], (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width('to buy') / 2 - 7, 179), group='ui', z=9998)
                        if self.interacted:
                            self.e['Sounds'].play('jingle')
                            self.scrap -= nearby_item.price
                            player = self.e['Game'].player
                            if nearby_item.category == 'shop':
                                if nearby_item.type == 'heart':
                                    player.max_health += 1
                                    player.health = min(player.max_health, player.health + 1)
                                if nearby_item.type == 'potion':
                                    player.health = min(player.max_health, player.health + (player.max_health - player.health) * 0.2 + 2)
                                else:
                                    self.owned_upgrades[nearby_item.type] += 1
                            elif nearby_item.category == 'weapon':
                                if not player.alt_weapon:
                                    player.alt_weapon = Weapon(nearby_item.type, player)
                                else:
                                    player.weapon = Weapon(nearby_item.type, player)
                            
                            self.interactables.remove(nearby_item)
                            for j in range(25):
                                self.e['EntityGroups'].add(pp.vfx.Spark((nearby_item.pos[0], nearby_item.pos[1] - 16 + math.cos(self.e['Window'].time * 1.2 + 0.1 * nearby_item.pos[0]) * 4.5), random.random() * math.pi * 2, size=(random.randint(6, 10), random.randint(1, 2)), speed=random.random() * 60 + 60, decay=random.random() * 4 + 2, color=(254, 252, 211), z=300), 'vfx')
                    elif self.interacted:
                        self.e['Sounds'].play('denied', 0.5)
                elif self.closest_entity[0]:
                    self.e['Text']['small_font'].renderzb('to interact', (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width('to interact') / 2 + 6, 182), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                    self.e['Renderer'].blit(self.e['Assets'].images['misc']['e'], (self.e['Game'].display.get_width() / 2 - self.e['Text']['small_font'].width('to interact') / 2 - 7, 179), group='ui', z=9998)
                    if self.interacted:
                        self.closest_entity[0].interact()
            
        if self.dialogue[0]:
            fresh = not self.dialogue_state['progress']
            if not len(self.dialogue[1]):
                # dialogue hide animation
                self.dialogue_state['ui_offset'] += (60 - self.dialogue_state['ui_offset']) * self.e['Window'].dt * 10
            else:
                self.dialogue_state['ui_offset'] += (0 - self.dialogue_state['ui_offset']) * self.e['Window'].dt * 10
                if self.dialogue_state['ui_offset'] < 0.5:
                    self.dialogue_state['ui_offset'] = 0
                if self.dialogue_state['ui_offset'] < 10:
                    last_progress = self.dialogue_state['progress']
                    self.dialogue_state['progress'] += self.e['Window'].dt
                    if (last_progress % (1 / 30)) > (self.dialogue_state['progress'] % (1 / 30)):
                        if int(self.dialogue_state['progress'] * 30) < len(self.dialogue[1][0]):
                            char = self.dialogue[1][0][int(self.dialogue_state['progress'] * 30)]
                            if char.lower() not in {' ', ',', '.', '!', '?', '-', 'a', 'e', 'i', 'o', 'u', 'h'}:
                                if char.lower() in {'w', 'r', 'y', 's', 'f', 'l', 'z', 'v', 'n', 'm'}:
                                    self.e['Sounds'].play(f'{self.dialogue[0].type}_voice', volume=0.15)
                                else:
                                    self.e['Sounds'].play(f'{self.dialogue[0].type}_voice', volume=0.3)
            portrait_img = self.e['Assets'].images['portraits'][self.dialogue[0].type]
            self.e['Renderer'].blit(portrait_img, (5 - self.dialogue_state['ui_offset'], self.e['Game'].display.get_height() - 5 - portrait_img.get_height()), group='ui', z=9998.5)
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['portrait_frame'], (3 - self.dialogue_state['ui_offset'], self.e['Game'].display.get_height() - 7 - portrait_img.get_height()), group='ui', z=9998.6)
            self.e['Text']['small_font'].renderzb(self.dialogue[0].name, (50, self.e['Game'].display.get_height() - 5 - portrait_img.get_height() + self.dialogue_state['ui_offset']), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998.5, group='ui')

            banner_bg = pygame.Surface((self.e['Game'].display.get_width(), 10 + portrait_img.get_height()), pygame.SRCALPHA)
            banner_bg.fill((38, 27, 46, 110))
            self.e['Renderer'].blit(banner_bg, (0, self.e['Game'].display.get_height() - banner_bg.get_height() + self.dialogue_state['ui_offset']), group='ui', z=9998.4)

            if len(self.dialogue[1]):
                msg = self.dialogue[1][0]
                self.e['Text']['small_font'].renderzb(msg[:int(self.dialogue_state['progress'] * 30)], (50, self.e['Game'].display.get_height() + 7 - portrait_img.get_height() + self.dialogue_state['ui_offset']), line_width=self.e['Game'].display.get_width() - 60, color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998.5, group='ui')
                if self.interacted and (not fresh):
                    self.dialogue[1].pop(0)
                    self.dialogue_state['progress'] = 0
                    self.e['Sounds'].play('tap')
            else:
                if self.dialogue_state['ui_offset'] > 55:
                    if self.dialogue[0].type == 'gary':
                        self.enchanting = True
                        self.e['Sounds'].play('ui_slide', volume=0.35)
                    # fully ends dialogue state
                    self.dialogue = [None, []]
                    self.dialogue_state['progress'] = 0

        self.pointer_anim.update(self.e['Window'].dt)
        self.popup_pointer_anim.update(self.e['Window'].dt)

        if self.enchanting:
            self.enchanting_offset += -self.enchanting_offset * self.e['Window'].dt * 5
            if self.enchanting_offset < 0.7:
                self.enchanting_offset = 0
        else:
            self.enchanting_offset += (200 - self.enchanting_offset) * self.e['Window'].dt * 9
            if self.enchanting_offset > 199.3:
                self.enchanting_offset = 200
        if self.enchanting_offset < 190:
            weapon = self.e['Game'].player.weapon
            if self.enchant_anim_progress:
                self.enchant_anim_progress += self.e['Window'].dt
                if self.enchant_anim_progress > 2.5:
                    self.enchant_anim_progress = 0
                    self.enchant_anim_offset = 0
                elif self.enchant_anim_progress > 1.34:
                    self.enchant_anim_offset += -self.enchant_anim_offset * self.e['Window'].dt * 9
                    if self.enchant_anim_progress - self.e['Window'].dt <= 1.34:
                        # enchant when the animation reverses direction to reveal the enchant
                        weapon.enchant()
                        if len(weapon.enchant_list):
                            for i, enchant in enumerate(weapon.enchant_list):
                                self.e['EntityGroups'].add(Slash((0, 65 + 26 * i), 0, (7, 7), color=(254, 252, 211), speed=11, decay=40, group='ui', z=9999.5), 'vfx')
                                self.e['EntityGroups'].add(Slash((0, 75 + 26 * i), 0, (10, 7), color=(254, 252, 211), speed=14, decay=40, group='ui', z=9999.5), 'vfx')
                                self.e['EntityGroups'].add(Slash((0, 65 + 26 * i), 0, (9, 9), color=(38, 27, 46), speed=11, decay=35, group='ui', z=9999.4), 'vfx')
                                self.e['EntityGroups'].add(Slash((0, 75 + 26 * i), 0, (12, 9), color=(38, 27, 46), speed=14, decay=35, group='ui', z=9999.4), 'vfx')
                else:
                    self.enchant_anim_offset += (200 - self.enchant_anim_offset) * self.e['Window'].dt * 5
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['full_fade'], (-self.enchanting_offset, 0), z=9980, group='ui')
            self.e['Text']['large_font'].renderzb('Blacksmith Enchant', (4 - self.e['State'].enchanting_offset, 4), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
            self.e['Text']['small_font'].renderzb(weapon.title, (4 - self.e['State'].enchanting_offset, 33), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
            weapon_img = self.e['Assets'].images['weapons'][f'{weapon.type}_icon']
            self.e['Renderer'].blit(weapon_img, (4 - self.e['State'].enchanting_offset, 41), z=9998, group='ui')
            self.e['Renderer'].blit(self.e['Assets'].images['weapons'][f'{weapon.type}_flat'], (8 - self.e['State'].enchanting_offset, 44), z=9997, group='ui')
            self.e['Game'].player.weapon.render_stars((4 - self.e['State'].enchanting_offset, 41 + weapon_img.get_height() - 3), group='ui', z=9999)
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['scrap'], (4 - self.e['State'].enchanting_offset, 21), z=9998, group='ui')
            self.e['Text']['small_font'].renderzb(f'{self.scrap:,}', (13 - self.e['State'].enchanting_offset, 22), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')

            
            self.render_weapon_enchants(weapon, offset=(self.enchanting_offset + self.enchant_anim_offset, 0))

            enchanting_options = ['Back', 'Strip Enchants', 'Enhance']
            if not len(weapon.enchant_list):
                enchanting_options = ['Back', 'Enchant']

            if (not self.popup[2]):
                if self.e['Controllers'].pressed('move_y'):
                    self.enchanting_selection_index = (self.enchanting_selection_index - 1) % len(enchanting_options)
                    self.pointer_anim.reset()
                    self.e['Sounds'].play('tap')
                if self.e['Controllers'].pressed_neg('move_y'):
                    self.enchanting_selection_index = (self.enchanting_selection_index + 1) % len(enchanting_options)
                    self.pointer_anim.reset()
                    self.e['Sounds'].play('tap')
            
            for i, option in enumerate(enchanting_options):
                if i == self.enchanting_selection_index:
                    self.e['Renderer'].blit(self.pointer_anim.img, (3 - self.e['State'].enchanting_offset, self.e['Game'].display.get_height() - 12 * (i + 2) - 1), z=9998, group='ui')
                option_r = pygame.Rect(-self.e['State'].enchanting_offset, self.e['Game'].display.get_height() - 12 * (i + 2) - 2, 70, 10)
                hovering = option_r.collidepoint(self.e['Game'].mpos) or self.e['Game'].controller_mode
                text_offset = 0
                if hovering and (not self.popup[2]):
                    if not self.e['Game'].controller_mode:
                        if self.enchanting_selection_index != i:
                            self.enchanting_selection_index = i
                            self.pointer_anim.reset()
                            self.e['Sounds'].play('tap')
                    if self.enchanting_selection_index == i:
                        if (self.e['Input'].pressed('shoot') or self.e['Controllers'].pressed('interact')) and (not self.enchant_anim_progress):
                            self.e['Input'].consume('shoot')
                            self.e['Controllers'].consume('interact')
                            self.e['Sounds'].play('tap')
                            if option == 'Back':
                                self.enchanting = False
                            if option in ['Enchant', 'Enhance']:
                                if self.scrap >= weapon.enchant_price:
                                    self.scrap -= weapon.enchant_price
                                    self.e['Sounds'].play('enchant', volume=1.0)
                                    self.enchant_anim_progress = 0.01
                                else:
                                    self.e['Sounds'].play('denied', 0.5)
                            if option == 'Strip Enchants':
                                self.popup = ['Are you sure you want to strip all enchants?', 200, self.strip_enchant_callback, 0]
                        text_offset = math.sin(self.e['Window'].time * 9) * 2.5 + 2.5
                if option in ['Enchant', 'Enhance']:
                    self.e['Renderer'].blit(self.e['Assets'].images['misc']['scrap'], (46 - self.e['State'].enchanting_offset + text_offset, self.e['Game'].display.get_height() - 12 * (i + 2) - 1), z=9998, group='ui')
                    color = (254, 252, 211)
                    if self.scrap < weapon.enchant_price:
                        color = (191, 60, 96)
                    self.e['Text']['small_font'].renderzb(str(weapon.enchant_price), (54 - self.e['State'].enchanting_offset + text_offset, self.e['Game'].display.get_height() - 12 * (i + 2)), color=color, bgcolor=(38, 27, 46), z=9998, group='ui')
                self.e['Text']['small_font'].renderzb(option, (14 - self.e['State'].enchanting_offset + text_offset, self.e['Game'].display.get_height() - 12 * (i + 2)), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')

        if self.popup[0]:
            if self.popup[2]:
                if self.e['Controllers'].pressed('move_x') or self.e['Controllers'].pressed_neg('move_x'):
                    self.popup[3] = 1 - self.popup[3]
                    self.popup_pointer_anim.reset()
                    self.e['Sounds'].play('tap')
            if self.popup[2]:
                self.popup[1] += -self.popup[1] * self.e['Window'].dt * 10
            else:
                self.popup[1] += (200 - self.popup[1]) * self.e['Window'].dt * 10
            popup_bg = self.e['Assets'].images['misc']['popup_bg']
            popup_tl = (self.e['Game'].display.get_width() / 2 - popup_bg.get_width() / 2, self.e['Game'].display.get_height() / 2 - popup_bg.get_height() / 2 + self.popup[1])
            self.e['Renderer'].blit(popup_bg, popup_tl, z=9999, group='ui')
            self.e['Text']['small_font'].renderzb(self.popup[0], (popup_tl[0] + 5, popup_tl[1] + 5), color=(254, 252, 211), bgcolor=(38, 27, 46), line_width=popup_bg.get_width() - 10, z=9999.5, group='ui')
            for i, option in enumerate(['No', 'Yes']):
                option_width = self.e['Text']['small_font'].width(option)
                option_pos = (popup_tl[0] + 30 - option_width / 2 + i * (popup_bg.get_width() - 30 * 2), popup_tl[1] + popup_bg.get_height() - 11)
                if i == self.popup[3]:
                    self.e['Renderer'].blit(self.popup_pointer_anim.img, (option_pos[0] - 10, option_pos[1] - 1), z=9999.5, group='ui')
                option_r = pygame.Rect(option_pos[0] - 4, option_pos[1] - 2, option_width + 4, 12)
                hovering = option_r.collidepoint(self.e['Game'].mpos) or self.e['Game'].controller_mode
                text_offset = 0
                if hovering and self.popup[2]:
                    if not self.e['Game'].controller_mode:
                        if self.popup[3] != i:
                            self.popup[3] = i
                            self.popup_pointer_anim.reset()
                            self.e['Sounds'].play('tap')
                    if self.popup[3] == i:
                        if (self.e['Input'].pressed('shoot') or self.e['Controllers'].pressed('interact')):
                            self.e['Input'].consume('shoot')
                            self.e['Controllers'].consume('interact')
                            self.e['Sounds'].play('tap')
                            self.popup[2](option == 'Yes')
                            self.popup[2] = None
                        text_offset = math.sin(self.e['Window'].time * 9) * 2.5 + 2.5
                self.e['Text']['small_font'].renderzb(option, (option_pos[0] + text_offset, option_pos[1]), color=(254, 252, 211), bgcolor=(38, 27, 46), line_width=popup_bg.get_width() - 10, z=9999.5, group='ui')
            
        if (not (self.e['Game'].player.dead or self.e['Transition'].progress or self.e['Transition'].level_end or self.ui_busy)) or (self.e['State'].right_inv_offset):
            self.render_ability_cooldown(WEAPON_STATS[self.e['Game'].player.weapon.type]['primary'], (self.e['Game'].display.get_width() - 40 + self.e['State'].right_inv_offset, self.e['Game'].display.get_height() - 22), z=9998, group='ui')
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['mouse_left'], (self.e['Game'].display.get_width() - 28 + self.e['State'].right_inv_offset, self.e['Game'].display.get_height() - 13), z=9999, group='ui')
            self.render_ability_cooldown(WEAPON_STATS[self.e['Game'].player.weapon.type]['secondary'], (self.e['Game'].display.get_width() - 20 + self.e['State'].right_inv_offset, self.e['Game'].display.get_height() - 22), z=9998, group='ui')
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['mouse_right'], (self.e['Game'].display.get_width() - 8 + self.e['State'].right_inv_offset, self.e['Game'].display.get_height() - 13), z=9999, group='ui')

            for i, upgrade in enumerate([upgrade for upgrade in self.owned_upgrades if self.owned_upgrades[upgrade]]):
                upgrade_img = self.e['Assets'].images['upgrades'][upgrade + '_b']
                self.e['Renderer'].blit(upgrade_img, (self.e['Game'].display.get_width() - upgrade_img.get_width() - 4 + self.e['State'].right_inv_offset, self.e['Minimap'].ui_size[1] + 10 + i * 13), z=9998, group='ui')
                amt_text = f'{self.owned_upgrades[upgrade]}x'
                self.e['Text']['small_font'].renderzb(amt_text, (self.e['Game'].display.get_width() - self.e['Text']['small_font'].width(amt_text) - 23 + self.e['State'].right_inv_offset, self.e['Minimap'].ui_size[1] + 15 + i * 13), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
        
            if self.e['Settings'].setting('show_fps') == 'enabled':
                fps_text = f'FPS: {int(self.e["Window"].fps)}'
                self.e['Text']['small_font'].renderzb(fps_text, (self.e['Game'].display.get_width() - self.e['Minimap'].ui_size[0] - 9 - self.e['Text']['small_font'].width(fps_text) + self.e['State'].right_inv_offset, 4), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')

        if not (self.e['Game'].player.dead or self.e['Transition'].progress or self.e['Transition'].level_end or self.ui_busy):
            for notification in self.notifications:
                self.e['Text'][notification[3]].renderzb(notification[0], (self.e['Game'].display.get_width() / 2 - self.e['Text'][notification[3]].width(notification[0]) / 2, notification[1]), color=(254, 252, 211), bgcolor=(38, 27, 46), z=10001.5, group='ui')

            if not (self.e['Transition'].progress or self.e['Transition'].level_end or self.title or self.e['HUD'].hide_ui):
                active_effects = [effect for effect in self.effects if self.effects[effect][0]]
                for i, effect in enumerate(active_effects):
                    dur = self.effects[effect][0]
                    offset_x = (i - (len(active_effects) - 1) / 2) * 10
                    ratio = 1 - dur / self.effects[effect][1]
                    img = self.e['Assets'].images['upgrades'][f'{effect}_b'].copy()
                    img_front = img.copy()
                    img.set_alpha(80)
                    if ratio < 1:
                        img_front.blit(pygame.Surface((img.get_width(), int((ratio * 0.75 + 0.125) * img.get_height()))), (0, 0))
                    img_front.set_colorkey((0, 0, 0))
                    self.e['Renderer'].blit(img, (self.e['Game'].player.center[0] - self.e['Game'].camera[0] - img.get_width() // 2 + offset_x, self.e['Game'].player.center[1] + 13 - self.e['Game'].camera[1] - img.get_height() // 2), z=9994, group='ui')
                    self.e['Renderer'].blit(img_front, (self.e['Game'].player.center[0] - self.e['Game'].camera[0] - img.get_width() // 2 + offset_x, self.e['Game'].player.center[1] + 13 - self.e['Game'].camera[1] - img.get_height() // 2), z=9995, group='ui')
                    self.e['Renderer'].blit(self.e['Assets'].images['upgrades']['frame'], (self.e['Game'].player.center[0] - self.e['Game'].camera[0] - img.get_width() // 2 + offset_x, self.e['Game'].player.center[1] + 13 - self.e['Game'].camera[1] - img.get_height() // 2), z=9996, group='ui')
    
        self.closest_entity = [None, 99999]
                
