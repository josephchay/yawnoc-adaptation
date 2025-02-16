import math

import pygame

from . import pygpen as pp

from .state import generate_description, UPGRADE_INFO

UPGRADES_PER_ROW = 9

class PauseMenu(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        self.pointer_anim = self.e['EntityDB']['misc'].animations['pointer'].copy()

        self.black_surf = pygame.Surface(self.e['Game'].display.get_size(), pygame.SRCALPHA)

        self.reset()

    def reset(self):
        # row, column
        self.selection = [1, 0]

        self.pause_offset = 200
        self.pause_direction = 1

        self.pointer_anim.reset()
    
    @property
    def paused(self):
        return self.pause_offset < 199

    @property
    def options(self):
        return ['End Run', 'Resume']
    
    def pause(self):
        self.pause_direction = -1
        self.selection = [0, 0]

    def unpause(self):
        self.pause_direction = 1

    def update(self):
        self.pointer_anim.update(self.e['Window'].dt)

        if self.pause_direction == -1:
            self.pause_offset += (-self.pause_offset) * self.e['Window'].dt * 5
            if self.pause_offset < 0.5:
                self.pause_offset = 0
        else:
            self.pause_offset += (200 - self.pause_offset) * self.e['Window'].dt * 9
            if self.pause_offset > 199.5:
                self.pause_offset = 200

        if self.e['Input'].pressed('pause') or self.e['Controllers'].pressed('pause'):
            if not self.paused:
                if not self.e['State'].ui_busy:
                    self.pause()
            elif self.e['State'].popup[2]:
                self.e['State'].popup[2] = None
            else:
                self.unpause()

        if self.paused:
            if self.e['Controllers'].pressed('move_y'):
                if self.selection[1] == 0:
                    self.selection[0] -= 1
                    if self.selection[0] < 0:
                        self.selection = [0, 2]
                    else:
                        self.pointer_anim.reset()
                elif self.selection[1] == 1:
                    row = self.selection[0] // UPGRADES_PER_ROW
                    row_count = math.ceil(len(self.upgrade_list) / UPGRADES_PER_ROW)
                    if row + 1 >= row_count:
                        self.selection = [1, 0]
                        self.pointer_anim.reset()
                    else:
                        self.selection[0] += UPGRADES_PER_ROW
                elif self.selection[1] == 2:
                    if len(self.upgrade_list):
                        self.selection = [0, 1]
                    else:
                        self.selection = [1, 0]
                        self.pointer_anim.reset()
                self.e['Sounds'].play('tap')
            if self.e['Controllers'].pressed_neg('move_y'):
                if self.selection[1] == 0:
                    self.selection[0] += 1
                    if self.selection[0] >= len(self.options):
                        if len(self.upgrade_list):
                            # go to the first element of the last row
                            self.selection = [int((len(self.upgrade_list) - 1) // UPGRADES_PER_ROW) * UPGRADES_PER_ROW, 1]
                        else:
                            self.selection = [0, 2]
                    else:
                        self.pointer_anim.reset()
                elif self.selection[1] == 1:
                    row = self.selection[0] // UPGRADES_PER_ROW
                    if row == 0:
                        self.selection = [0, 2]
                    else:
                        self.selection[0] -= UPGRADES_PER_ROW
                elif self.selection[1] == 2:
                    self.selection = [0, 0]
                    self.pointer_anim.reset()
                self.e['Sounds'].play('tap')
            if self.e['Controllers'].pressed('move_x'):
                if self.selection[1] == 1:
                    row = self.selection[0] // UPGRADES_PER_ROW
                    self.selection[0] = (self.selection[0] + 1) % UPGRADES_PER_ROW + row * UPGRADES_PER_ROW
                    if self.selection[0] >= len(self.upgrade_list):
                        self.selection[0] = row * UPGRADES_PER_ROW
                elif self.selection[1] == 2:
                    self.selection[0] = 1 - self.selection[0]
                self.e['Sounds'].play('tap')
            if self.e['Controllers'].pressed_neg('move_x'):
                if self.selection[1] == 1:
                    row = self.selection[0] // UPGRADES_PER_ROW
                    self.selection[0] = min((self.selection[0] - 1) % UPGRADES_PER_ROW + row * UPGRADES_PER_ROW, len(self.upgrade_list) - 1)
                elif self.selection[1] == 2:
                    self.selection[0] = 1 - self.selection[0]
                self.e['Sounds'].play('tap')
    
    def end_run(self, result):
        if result:
            self.reset()
            self.e['Transition'].transition(callback=self.e['Game'].restart)

    @property
    def upgrade_list(self):
        return [upgrade for upgrade in self.e['State'].owned_upgrades if self.e['State'].owned_upgrades[upgrade]]

    def render(self):
        if self.paused:
            items_tl = (14, 14 - self.pause_offset)

            weapon_hovering = None
            weapons = [self.e['Game'].player.weapon]
            if self.e['Game'].player.alt_weapon:
                weapons.append(self.e['Game'].player.alt_weapon)
            for i, weapon in enumerate(weapons):
                alpha = 150
                if (i, 2) == tuple(self.selection):
                    alpha = 255
                img = self.e['Assets'].images['weapons'][f'{weapon.type}_icon'].copy()
                img.set_alpha(alpha)
                weapon_r = pygame.Rect(items_tl[0] + 40 * i, items_tl[1] + 28 - img.get_height() / 2, img.get_width(), img.get_height())
                hovering = weapon_r.collidepoint(self.e['Game'].mpos) or self.e['Game'].controller_mode
                if hovering and (not self.e['State'].popup[2]):
                    if not self.e['Game'].controller_mode:
                        if (i, 2) != tuple(self.selection):
                            self.selection = [i, 2]
                            self.e['Sounds'].play('tap')
                    if (i, 2) == tuple(self.selection):
                        weapon_info = UPGRADE_INFO[weapon.type]
                        self.e['Text']['small_font'].renderzb(weapon_info['name'], (70, self.e['Game'].display.get_height() - 36), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                        self.e['Text']['small_font'].renderzb(weapon_info['desc'], (70, self.e['Game'].display.get_height() - 24), line_width=self.e['Game'].display.get_width() - 80, color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                        weapon_hovering = weapon
                
                self.e['Renderer'].blit(img, (items_tl[0] + 40 * i, items_tl[1] + 28 - img.get_height() / 2), z=9998, group='ui')
                weapon.render_stars((items_tl[0] + 40 * i, items_tl[1] + 28 - img.get_height() / 2 + img.get_height() - 3), group='ui', z=9999)

            scrap_img = self.e['Assets'].images['misc']['scrap']
            self.e['Renderer'].blit(scrap_img, (items_tl[0], items_tl[1] - scrap_img.get_height() / 2), z=9997, group='ui')
            self.e['Text']['small_font'].renderzb(f'{self.e["State"].scrap:,}', (items_tl[0] + 9, items_tl[1] - 3), color=(254, 252, 211), bgcolor=(38, 27, 46), offset=(0, 0), group='ui', z=9997)

            score_text = f'Wave: {self.e["State"].wave}'
            self.e['Text']['small_font'].renderzb(score_text, (items_tl[0], items_tl[1] + 8), color=(254, 252, 211), bgcolor=(38, 27, 46), offset=(0, 0), group='ui', z=9998)

            if weapon_hovering:
                self.e['State'].render_weapon_enchants(weapon_hovering, (-11, 62 - (items_tl[1] + 48)))
            else:
                for i, upgrade in enumerate(self.upgrade_list):
                    alpha = 150
                    if (i, 1) == tuple(self.selection):
                        alpha = 255
                    upgrade_img = self.e['Assets'].images['upgrades'][upgrade + '_b'].copy()
                    upgrade_img.set_alpha(alpha)
                    upgrade_r = pygame.Rect(items_tl[0] + (i % UPGRADES_PER_ROW) * 20, items_tl[1] + 48 + (i // UPGRADES_PER_ROW) * 20, *upgrade_img.get_size())
                    hovering = upgrade_r.collidepoint(self.e['Game'].mpos) or self.e['Game'].controller_mode
                    if hovering and (not self.e['State'].popup[2]):
                        if not self.e['Game'].controller_mode:
                            if (i, 1) != tuple(self.selection):
                                self.selection = [i, 1]
                                self.e['Sounds'].play('tap')
                        if (i, 1) == tuple(self.selection):
                            upgrade_info = UPGRADE_INFO[upgrade]
                            self.e['Text']['small_font'].renderzb(upgrade_info['name'], (70, self.e['Game'].display.get_height() - 36), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
                            upgrade_desc = generate_description(upgrade, self.e['State'].owned_upgrades[upgrade])
                            self.e['Text']['small_font'].renderzb(upgrade_desc, (70, self.e['Game'].display.get_height() - 24), line_width=self.e['Game'].display.get_width() - 80, color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')

                    self.e['Renderer'].blit(upgrade_img, upgrade_r.topleft, z=9997, group='ui')
                    amt_text = f'{self.e["State"].owned_upgrades[upgrade]}x'
                    self.e['Text']['small_font'].renderzb(amt_text, (items_tl[0] + (i % UPGRADES_PER_ROW) * 20 + 14 - self.e['Text']['small_font'].width(amt_text) / 2, items_tl[1] + 60 + (i // UPGRADES_PER_ROW) * 20), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')

            for i, option in enumerate(self.options):
                if (i, 0) == tuple(self.selection):
                    self.e['Renderer'].blit(self.pointer_anim.img, (3 - self.pause_offset, self.e['Game'].display.get_height() - 12 * (i + 2) - 1), z=9998, group='ui')
                option_r = pygame.Rect(-self.pause_offset, self.e['Game'].display.get_height() - 12 * (i + 2) - 2, 70, 10)
                hovering = option_r.collidepoint(self.e['Game'].mpos) or self.e['Game'].controller_mode
                text_offset = 0
                if hovering and (not self.e['State'].popup[2]):
                    if not self.e['Game'].controller_mode:
                        if tuple(self.selection) != (i, 0):
                            self.selection = [i, 0]
                            self.pointer_anim.reset()
                            self.e['Sounds'].play('tap')
                    if tuple(self.selection) == (i, 0):
                        if self.e['Input'].pressed('shoot') or self.e['Controllers'].pressed('interact'):
                            self.e['Input'].consume('shoot')
                            self.e['Controllers'].consume('interact')
                            self.e['Sounds'].play('tap')
                            if option == 'Resume':
                                self.pause_direction = 1
                            if option == 'End Run':
                                self.e['State'].popup = ['Are you sure you want to end this run?', 200, self.end_run, 0]
                        text_offset = math.sin(self.e['Window'].time * 9) * 2.5 + 2.5

                self.e['Text']['small_font'].renderzb(option, (14 - self.pause_offset + text_offset, self.e['Game'].display.get_height() - 12 * (i + 2)), color=(254, 252, 211), bgcolor=(38, 27, 46), z=9998, group='ui')
            
            self.e['Renderer'].blit(self.e['Assets'].images['misc']['full_fade'], (-self.pause_offset, 0), z=9980, group='ui')

            self.black_surf.fill((38, 27, 46, (200 - self.pause_offset) * 0.3))
            self.e['Renderer'].blit(self.black_surf, (0, 0), z=9980, group='ui')