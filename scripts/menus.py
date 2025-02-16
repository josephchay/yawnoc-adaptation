import sys
import math

import pygame

from . import pygpen as pp

from .bezier import generate_line_chain_vfx
from .weapon import Weapon, WEAPON_STATS, WEAPON_NAMES

MENU_WEAPONS = ['rifle', 'pistol', 'shotgun']

MAIN_MENU_OPTIONS = ['Play', 'Options', 'Quit']

WEAPON_UNLOCKS = {
    'rifle': 0,
    'pistol': 4,
    'shotgun': 8,
}

WEAPON_ABILITY_NAMES = {
    'piercing_round': 'Piercing Round',
    'grenade': 'Grenade',
    'birdshot': 'Birdshot',
    'quake': 'Quake',
    'warp': 'Warp',
    'warp_mark': 'Warp Mark',
    'arrow_barrage': 'Arrow Barrage',
    'arrow_shoot': 'Arrow',
}

SETTING_SUBMENUS = ['Video', 'Audio', 'Keyboard Input', 'Controller Input', 'Accessibility', 'Back']

SETTINGS = {
    'fps_cap': {
        'name': 'FPS Cap',
        'options': ['30', '60', '90', '120', '144', '165', '240', 'uncapped'],
        'submenu': 'video',
    },
    'fullscreen': {
        'name': 'Fullscreen',
        'options': ['disabled', 'enabled'],
        'submenu': 'video',
    },
    'windowed_resolution': {
        'name': 'Windowed Resolution',
        'options': ['384x216', '768x432', '1152x648', '1536x864', '1920x1080', 'native'],
        'submenu': 'video',
    },
    'master_volume': {
        'name': 'Master Volume',
        'options': ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%'],
        'submenu': 'audio',
    },
    'sfx_volume': {
        'name': 'SFX Volume',
        'options': ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%'],
        'submenu': 'audio',
    },
    'music_volume': {
        'name': 'Music Volume',
        'options': ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%'],
        'submenu': 'audio',
    },
    'aim_assist': {
        'name': 'Controller Aim Assist',
        'options': ['0%', '50%', '100%'],
        'submenu': 'accessibility',
    },
    'outline': {
        'name': 'Player Outline',
        'options': ['disabled', 'enabled'],
        'submenu': 'accessibility',
    },
    'show_fps': {
        'name': 'Show FPS',
        'options': ['disabled', 'enabled'],
        'submenu': 'video',
    },
    'swap_trigger_bumper': {
        'name': 'Swap Bumpers/Triggers',
        'options': ['disabled', 'enabled'],
        'submenu': 'controller input',
    },
    'pink_player': {
        'name': 'Pink Player',
        'options': ['disabled', 'enabled'],
        'submenu': 'accessibility',
    },
    'saturation': {
        'name': 'Saturation',
        'options': ['70%', '80%', '90%', '95%', '100%'],
        'submenu': 'video',
    },
    'back': {
        'name': 'Back',
        'options': [],
        'submenu': 'all',
    },
}

class Menus(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        self.weapon_ui_beziers = [generate_line_chain_vfx('menu_item', 'slow_in', [0, 0]) for i in range(len(WEAPON_NAMES))]
        self.main_ui_beziers = [generate_line_chain_vfx('menu_item_text_large', 'slow_in', [0, 0]) for i in range(len(MAIN_MENU_OPTIONS))]
        self.last_hover = None

        # default beziers to hidden
        for bezier in self.weapon_ui_beziers + self.main_ui_beziers:
            bezier.rate = -abs(bezier.rate)

        self.submenu = 'title'

        self.x_offset = 0
        self.next_menu = None

        self.settings_hover_i = 0
        self.pointer_anim = self.e['EntityDB']['misc'].animations['pointer'].copy()
        self.menu_hover_i = 0

        self.settings_submenu = None
        self.updating_binding = None
        self.last_settings_list = None

        if self.e['Settings'].steamdeck:
            if 'fullscreen' in SETTINGS:
                del SETTINGS['fullscreen']

    @property
    def cm(self):
        return self.e['Game'].controller_mode
    
    @property
    def interacted(self):
        return self.e['Input'].pressed('shoot') or self.e['Controllers'].pressed('interact')
    
    def consume_interaction(self):
        self.e['Input'].consume('shoot')
        self.e['Controllers'].consume('interact')

    def update(self):
        for bezier in self.weapon_ui_beziers + self.main_ui_beziers:
            bezier.update(self.e['Window'].dt)
        if self.e['Controllers'].pressed('move_y'):
            self.shift_selection(1)
        if self.e['Controllers'].pressed_neg('move_y'):
            self.shift_selection(-1)

        if self.e['Input'].pressed('pause') or self.e['Controllers'].pressed('pause'):
            if self.submenu == 'weapon_select':
                self.next_menu = 'title'
            if self.submenu == 'settings':
                if self.settings_submenu:
                    self.settings_submenu = None
                else:
                    self.next_menu = 'title'
            self.e['Sounds'].play('tap')

    def shift_selection(self, offset):
        if self.e['State'].title:
            if self.submenu == 'settings':
                if self.last_settings_list:
                    self.settings_hover_i = (self.settings_hover_i + offset) % len(self.last_settings_list)
                    self.e['Sounds'].play('tap')
            if self.submenu == 'title':
                self.menu_hover_i = (self.menu_hover_i + offset) % len(MAIN_MENU_OPTIONS)
            if self.submenu == 'weapon_select':
                self.menu_hover_i = (self.menu_hover_i + offset) % len(MENU_WEAPONS)
            if offset:
                self.pointer_anim.reset()

    def end_title(self):
        self.e['State'].title = False
        self.e['State'].shopping = 1
        self.e['State'].shop_land()
        if self.e['State'].season == 'fall':
            self.e['Music'].play('fall_shop')
        else:
            self.e['Music'].play('summer_shop')

    def unlocked(self, weapon):
        return WEAPON_UNLOCKS[weapon] <= self.e['State'].record
    
    def get_binding_name(self, binding):
        if binding[0] == 'mouse':
            if 0 < binding[1] < 6:
                return ['mouse left', 'mouse wheel', 'mouse right', 'mouse scroll up', 'mouse scroll down'][binding[1] - 1]
            return '???'
        elif binding[0] == 'button':
            return pygame.key.name(binding[1])
        return '???'
    
    def binding_callback(self, new_binding):
        self.e['Input'].config[self.updating_binding] = new_binding
        self.e['Input'].save_config()
        self.updating_binding = None

    def render(self):
        new_hover = None
        if self.e['State'].title:
            if self.next_menu:
                self.x_offset += (200 - self.x_offset) * self.e['Window'].dt * 3
                if self.x_offset > 180:
                    self.submenu = self.next_menu
                    self.next_menu = None
            else:
                self.x_offset += -self.x_offset * self.e['Window'].dt * 7
                if self.x_offset < 0.5:
                    self.x_offset = 0

            self.pointer_anim.update(self.e['Window'].dt)

            if self.submenu == 'settings':
                self.e['Renderer'].blit(self.e['Assets'].images['misc']['full_fade'], (-self.x_offset, 0), z=9000, group='ui')

                setting_gap = 140
                setting_y_gap = 13
                if not self.settings_submenu:
                    setting_list = {setting.lower(): {'name': setting, 'options': []} for setting in SETTING_SUBMENUS}
                elif self.settings_submenu.lower() == 'keyboard input':
                    setting_list = {binding: {'name': binding.replace('_', ' '), 'options': [], 'value': self.get_binding_name(self.e['Input'].config[binding])} for binding in self.e['Input'].config if binding != '__backspace'}
                    setting_list['reset'] = {'name': 'Reset Bindings', 'options': []}
                    setting_list['back'] = {'name': 'Back', 'options': []}
                elif self.settings_submenu.lower() == 'controller input':
                    if self.e['Controllers'].last:
                        setting_list = {
                            'device_id': {'name': f'Controller GUID: {self.e["Controllers"].last.guid}', 'options': []},
                            'device_name': {'name': f'Controller Name: {self.e["Controllers"].last.name}', 'options': []},
                            'swap_trigger_bumper': SETTINGS['swap_trigger_bumper'],
                            'back': {'name': 'Back', 'options': []},
                        }
                    else:
                        setting_list = {
                            'warning': {'name': 'No controller detected!', 'options': []},
                            'back': {'name': 'Back', 'options': []},
                        }
                elif self.settings_submenu:
                    setting_list = {setting: SETTINGS[setting] for setting in SETTINGS if (SETTINGS[setting]['submenu'] == self.settings_submenu.lower()) or (setting == 'back')}

                self.last_settings_list = setting_list

                for i, setting in enumerate(setting_list):
                    current_selection = self.e['Settings'].setting(setting)
                    setting_r = pygame.Rect(0, 13 + i * setting_y_gap, setting_gap + 30, 12)
                    hovering = setting_r.collidepoint(self.e['Game'].mpos)
                    if hovering or (self.cm and (self.settings_hover_i == i)):
                        if not self.cm:
                            if i != self.settings_hover_i:
                                self.pointer_anim.reset()
                                self.e['Sounds'].play('tap')
                            self.settings_hover_i = i
                        if self.interacted:
                            if setting == 'back':
                                if self.settings_submenu:
                                    self.settings_submenu = None
                                    self.e['Sounds'].play('tap')
                                    self.settings_hover_i = 0
                                else:
                                    self.next_menu = 'title'
                                    self.e['Sounds'].play('tap')
                                self.consume_interaction()
                            elif setting_list[setting]['name'] in SETTING_SUBMENUS:
                                self.settings_hover_i = 0
                                self.settings_submenu = setting
                                self.e['Sounds'].play('tap')
                                self.consume_interaction()
                            elif setting in self.e['Input'].config:
                                self.e['Input'].binding_listen_callback(self.binding_callback)
                                self.updating_binding = setting
                                self.e['Sounds'].play('tap')
                                self.consume_interaction()
                            elif setting == 'reset':
                                self.e['Input'].load_config('data/config/key_mappings_default.json')
                                self.e['Input'].save_config()
                    self.e['Text']['small_font'].renderzb(setting_list[setting]['name'], (-self.x_offset + 19, 16 + i * setting_y_gap), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9999, group='ui')
                    if 'value' in setting_list[setting]:
                        if setting == self.updating_binding:
                            setting_list[setting]['value'] = '<press>'
                        self.e['Text']['small_font'].renderzb(setting_list[setting]['value'], (-self.x_offset + 6 + setting_gap - self.e['Text']['small_font'].width(setting_list[setting]['value']) / 2, 16 + i * setting_y_gap), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9999, group='ui')
                    if self.settings_hover_i == i:
                        self.e['Renderer'].blit(self.pointer_anim.img, (-self.x_offset + 8, 15 + i * setting_y_gap), z=9999, group='ui')
                    if current_selection:
                        self.e['Text']['small_font'].renderzb(current_selection, (-self.x_offset + 6 + setting_gap - self.e['Text']['small_font'].width(current_selection) / 2, 16 + i * setting_y_gap), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9999, group='ui')
                        if self.settings_hover_i == i:
                            left_r = pygame.Rect(-self.x_offset - 6 + setting_gap - self.e['Text']['small_font'].width(current_selection) / 2 - 2, 14 + i * setting_y_gap, 10, 10)
                            right_r = pygame.Rect(-self.x_offset + 12 + setting_gap + self.e['Text']['small_font'].width(current_selection) / 2 - 2, 14 + i * setting_y_gap, 10, 10)
                            left_img = self.e['Assets'].images['misc']['arrow_l'].copy()
                            right_img = self.e['Assets'].images['misc']['arrow_r'].copy()
                            if left_r.collidepoint(self.e['Game'].mpos) or self.cm:
                                left_img.set_alpha(255)
                                if (self.e['Input'].pressed('shoot') and not self.cm) or (self.cm and self.e['Controllers'].pressed_neg('move_x')):
                                    self.e['Settings'].update(setting, setting_list[setting]['options'][(setting_list[setting]['options'].index(current_selection) - 1) % len(setting_list[setting]['options'])])
                                    self.e['Sounds'].play('tap')
                            else:
                                left_img.set_alpha(100)
                            if right_r.collidepoint(self.e['Game'].mpos) or self.cm:
                                right_img.set_alpha(255)
                                if (self.e['Input'].pressed('shoot') and not self.cm) or (self.cm and self.e['Controllers'].pressed('move_x')):
                                    self.e['Settings'].update(setting, setting_list[setting]['options'][(setting_list[setting]['options'].index(current_selection) + 1) % len(setting_list[setting]['options'])])
                                    self.e['Sounds'].play('tap')
                            else:
                                right_img.set_alpha(100)
                            self.e['Renderer'].blit(left_img, (-self.x_offset - 6 + setting_gap - self.e['Text']['small_font'].width(current_selection) / 2 + math.cos(self.e['Window'].time * 3) * 0.7, 14 + i * setting_y_gap), group='ui', z=9999)
                            self.e['Renderer'].blit(right_img, (-self.x_offset + 12 + setting_gap + self.e['Text']['small_font'].width(current_selection) / 2 - math.cos(self.e['Window'].time * 3) * 0.7, 14 + i * setting_y_gap), group='ui', z=9999)

            elif self.submenu == 'title':
                title_img = self.e['Assets'].images['misc']['title']
                self.e['Renderer'].blit(title_img, (self.e['Game'].display.get_width() / 2 - title_img.get_width() / 2, 26 + (1 if self.e['Window'].time % 1 < 0.25 else 0) - self.x_offset), z=9999, group='ui')

                for i, option in enumerate(MAIN_MENU_OPTIONS):
                    bezier = self.main_ui_beziers[i]
                    y_offset = min(bezier.time * 10, 4)
                    pos = (-self.x_offset, self.e['Game'].display.get_height() - (len(MAIN_MENU_OPTIONS) - i) * 24 - y_offset)
                    option_r = pygame.Rect(pos[0] - 1, pos[1] - 5 + y_offset, 104, 16)
                    hovering = option_r.collidepoint(self.e['Game'].mpos)
                    if hovering:
                        self.menu_hover_i = i
                    alpha = 140 + min(bezier.time * 400, 65)
                    self.e['Text']['large_font'].renderzb(option, (pos[0] + 6, pos[1]), color=(254, 252, 211, alpha + 50), bgcolor=(38, 27, 46, alpha + 50), z=9999, group='ui')
                    self.e['Renderer'].renderf(bezier.draw, offset=(pos[0], pos[1] + 18), z=9999, group='ui')
                    for offset in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        self.e['Renderer'].renderf(bezier.draw, offset=(pos[0] + offset[0], pos[1] + offset[1] + 18), color=(38, 27, 46), z=9998, group='ui')
                    if hovering or (self.cm and (self.menu_hover_i == i)):
                        if self.last_hover != option:
                            self.e['Sounds'].play('tap')
                        new_hover = option
                        bezier.rate = abs(bezier.rate)
                        if self.interacted:
                            if option == 'Quit':
                                pygame.quit()
                                sys.exit()
                            if option == 'Play':
                                self.next_menu = 'weapon_select'
                                self.e['Sounds'].play('tap')
                            if option == 'Options':
                                self.next_menu = 'settings'
                                self.e['Sounds'].play('tap')
                    else:
                        bezier.rate = -abs(bezier.rate)

            elif self.submenu == 'weapon_select':
                self.e['Text']['large_font'].renderzb('Weapon Select', (6 - self.x_offset, 6), color=(254, 252, 211, 255), bgcolor=(38, 27, 46, 255), z=9999, group='ui')

                for i, weapon in enumerate(MENU_WEAPONS):
                    bezier = self.weapon_ui_beziers[i]
                    y_offset = min(bezier.time * 10, 4)
                    pos = (-self.x_offset, 110 + i * 36 - y_offset)
                    option_r = pygame.Rect(pos[0] - 1, pos[1] - 29 + y_offset, 104, 29)
                    hovering = option_r.collidepoint(self.e['Game'].mpos)
                    if hovering:
                        self.menu_hover_i = i
                    alpha = 140 + min(bezier.time * 400, 65)
                    if self.unlocked(weapon):
                        self.e['Renderer'].renderf(bezier.draw, offset=pos, z=9999, group='ui')
                        for offset in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                            self.e['Renderer'].renderf(bezier.draw, offset=(pos[0] + offset[0], pos[1] + offset[1]), color=(38, 27, 46), z=9998, group='ui')
                        if hovering or (self.cm and (self.menu_hover_i == i)):
                            if self.last_hover != weapon:
                                self.e['Sounds'].play('tap')
                            new_hover = weapon
                            if not self.e['Transition'].progress:
                                self.e['Game'].player.weapon = Weapon(weapon, self.e['Game'].player)
                            bezier.rate = abs(bezier.rate)
                            if self.interacted:
                                self.e['Transition'].transition(self.end_title)
                                self.e['Sounds'].play('prepare', volume=0.45)
                        else:
                            bezier.rate = -abs(bezier.rate)
                        weapon_img = self.e['Assets'].images['weapons'][f'{weapon}_icon'].copy()
                        weapon_img.set_alpha(alpha + 50)
                        self.e['Renderer'].blit(weapon_img, (pos[0] + 33 - weapon_img.get_width() / 2, pos[1] - 26), z=9999, group='ui')
                        secondary = WEAPON_STATS[weapon]['secondary']
                        secondary_img = self.e['Assets'].images['upgrades'][f'{secondary}_b'].copy()
                        secondary_img.set_alpha(alpha + 50)
                        self.e['Renderer'].blit(secondary_img, (pos[0] + 8, pos[1] - 17), z=9999, group='ui')
                        if hovering:
                            self.e['Text']['small_font'].renderzb(WEAPON_NAMES[weapon], (pos[0] + 51, pos[1] - 24), color=(254, 252, 211, alpha + 50), bgcolor=(38, 27, 46, alpha + 50), z=9999, group='ui')
                            self.e['Text']['small_font'].renderzb(WEAPON_ABILITY_NAMES[secondary], (pos[0] + 27, pos[1] - 12), color=(254, 252, 211, alpha + 50), bgcolor=(38, 27, 46, alpha + 50), z=9999, group='ui')
                        else:
                            self.e['Text']['small_font'].renderz(WEAPON_NAMES[weapon], (pos[0] + 51, pos[1] - 24), color=(254, 252, 211, alpha + 50), z=9999, group='ui')
                            self.e['Text']['small_font'].renderz(WEAPON_ABILITY_NAMES[secondary], (pos[0] + 27, pos[1] - 12), color=(254, 252, 211, alpha + 50), z=9999, group='ui')
                    else:
                        bezier.rate = -abs(bezier.rate)
                        self.e['Text']['small_font'].renderz(f'   Clear wave {WEAPON_UNLOCKS[weapon]}\nto unlock.', (pos[0] + 16, pos[1] - 24), color=(254, 252, 211, alpha + 50), z=9999, group='ui')
        self.last_hover = new_hover

    
        