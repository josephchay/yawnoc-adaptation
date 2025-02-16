from scripts.crash_report import CRASH_REPORTER

try:
    import sys
    import time
    import math

    import pygame

    import scripts.pygpen as pp
    from scripts.player import Player
    from scripts.frenemy import Frenemy
    from scripts.tilemap import Tilemap
    from scripts.machines import Machines
    from scripts.minimap import Minimap
    from scripts.state import State
    from scripts.bullet import Bullet
    from scripts.highlife_map import HighlifeMap
    from scripts.transition import Transition
    from scripts.menus import Menus
    from scripts.hud import HUD
    from scripts.snow import Snow
    from scripts.settings import Settings
    from scripts.music import Music
    from scripts.aim_assist import AimAssist
    from scripts.setup import generate_shadow_anims
    from scripts.util import CONTROLLER_MAPPING, CONTROLLER_MAPPING_SWAPPED

    class Game(pp.PygpenGame):
        def load(self):
            base_resolution = (384, 216)

            self.settings = Settings()

            try:
                fps_cap = int(self.settings.setting('fps_cap'))
            except ValueError:
                fps_cap = 9999

            pp.init(
                self.settings.resolution,
                entity_path='data/images/entities',
                sounds_path='data/sfx',
                spritesheet_path='data/images/spritesheets',
                caption='Yawnoc',
                input_path='data/config/key_mappings.json',
                font_path='data/fonts',
                fps_cap=fps_cap,
                opengl=True,
                frag_path='data/shaders/main.frag',
            )

            self.e['Input'].enable_controllers(CONTROLLER_MAPPING_SWAPPED if self.e['Settings'].setting('swap_trigger_bumper') == 'enabled' else CONTROLLER_MAPPING, 'data')

            pygame.mouse.set_visible(False)

            self.display = pygame.Surface(base_resolution, pygame.SRCALPHA)
            self.hud_surf = self.display.copy()

            self.gm = pp.vfx.GrassManager('data/images/grass', tile_size=12, place_range=[0, 1], shade_amount=60)
            self.gm.enable_ground_shadows(shadow_radius=4, shadow_color=(38, 27, 46))

            self.e['Renderer'].set_groups(['default', 'ui'])

            self.player = None

            self.state = State()

            self.player = Player('player', (300, 300))
            self.e['EntityGroups'].add(self.player, 'entities')

            self.e['Assets'].enable('foliage')
            self.e['Assets'].load_folder('data/images/tiles', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/weapons', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/machines', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/patterns')
            self.e['Assets'].load_folder('data/images/misc', colorkey=(0, 0, 0), alpha=True)
            self.e['Assets'].load_folder('data/images/rigs', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/drops', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/upgrades', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/debris', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/decor', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/portraits', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/partner_icons', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/projectiles', colorkey=(0, 0, 0))
            self.e['Assets'].load_folder('data/images/leaf', colorkey=(0, 0, 0))

            # the stump is the only machine with an alpha
            self.e['Assets'].images['machines']['stump'] = pygame.image.load('data/images/machines/stump.png').convert_alpha()

            self.noise_tex = self.e['MGL'].pg2tx(self.e['Assets'].images['misc']['noise'])
            self.noise_tex.repeat_x = True
            self.noise_tex.repeat_y = True

            self.e['Assets'].images['misc']['full_fade'] = pygame.transform.scale(pygame.image.load('data/images/misc/fade.png').convert_alpha(), (100, self.display.get_height()))

            self.e['Assets'].images['misc']['shadow_small'].set_alpha(100)
            self.e['Assets'].images['misc']['shadow_medium'].set_alpha(100)
            self.e['Assets'].images['misc']['shadow_tiny'].set_alpha(100)

            BULLET_COLOR_LIST = ['red', 'blue', 'brown']

            self.e['Assets'].bullets = {color: [] for color in BULLET_COLOR_LIST}

            bullet_core = self.e['Assets'].images['misc']['bullet_core']
            for i in range(360):
                rotated_core = pygame.transform.rotate(bullet_core, i)
                bullet_border_colors = [pygame.transform.rotate(self.e['Assets'].images['misc'][f'bullet_{color}'], i) for color in BULLET_COLOR_LIST]
                for img in bullet_border_colors:
                    img.set_colorkey((0, 0, 0))
                rotated_core.set_colorkey((0, 0, 0))
                bullet_colors = [pygame.Surface((rotated_core.get_width() + 2, rotated_core.get_height() + 2)) for i in range(len(bullet_border_colors))]
                for offset in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    for i, img in enumerate(bullet_colors):
                        img.blit(bullet_border_colors[i], (1 + offset[0], 1 + offset[1]))
                for i, img in enumerate(bullet_colors):
                    img.blit(rotated_core, (1, 1))
                    img.set_colorkey((0, 0, 0))
                    self.e['Assets'].bullets[BULLET_COLOR_LIST[i]].append(img)

            self.menus = Menus()
            self.tilemap = Tilemap()
            self.hlmap = HighlifeMap()

            self.music = Music()
            self.aim_assist = AimAssist()

            self.camera = pp.Camera(base_resolution, slowness=0.2, tilemap_lock=self.tilemap)
            self.camera.set_target(self.player)

            self.machines = Machines()
            self.minimap = Minimap()

            self.transition = Transition()
            self.hud = HUD()
            self.snow = Snow()

            self.mpos = (0, 0)

            self.freeze_stack = []

            self.controller_mode = False
            self.controller_aim_offset = [30, 0]

            generate_shadow_anims(self)

            self.e['Sounds'].play('ambience', times=-1, volume=self.e['Settings'].sfx_volume * 0.6)

            self.state.load_title()

        def restart(self):
            self.player.pos = [300, 300]
            for entity in self.e['EntityGroups'].groups['entities']:
                if type(entity) == Bullet:
                    entity.life = 0
            self.state.reset()
            self.state.load_title()
            self.machines.reset(soft=True)
            self.player.max_health = 5.2
            self.player.health = self.player.max_health
            self.e['Transition'].direction = -1

        def handle_controller_switch(self):
            if self.controller_mode:
                if any(self.e['Mouse'].movement):
                    self.controller_mode = False
            else:
                if any([self.e['Controllers'].pressed(key) or self.e['Controllers'].pressed_neg(key) for key in ['move_x', 'move_y', 'aim_x', 'aim_y']]):
                    self.controller_mode = True

        def update(self):
            self.hud_surf.fill((0, 0, 0, 0))
            if not self.machines.high_life:
                self.display.fill((0, 0, 0, 0))
            else:
                self.display.fill((38, 27, 46))

            dt_scale = 1
            for freeze in self.freeze_stack[::-1]:
                dt_scale = min(freeze[0], dt_scale)
                freeze[1] = max(0, freeze[1] - self.e['Window'].dt)
                if not freeze[1]:
                    self.freeze_stack.remove(freeze)

            self.e['Window'].dt = min(self.e['Window'].dt * dt_scale, 0.1)

            if self.controller_mode:
                aim_offset = self.e['Controllers'].read_stick('aim_x', 'aim_y')
                if self.e['Settings'].aim_assist:
                    aim_offset = self.aim_assist.apply(aim_offset)
                if any(aim_offset):
                    aim_offset[0] *= 100
                    aim_offset[1] *= 100
                    self.controller_aim_offset = aim_offset.copy()
                self.mpos = (self.e['Game'].player.center[0] + self.controller_aim_offset[0] - self.camera[0], self.e['Game'].player.center[1] + self.controller_aim_offset[1] - self.camera[1])
            else:
                self.mpos = (self.e['Mouse'].pos[0] * (self.e['Game'].display.get_width() / self.e['Window'].dimensions[0]), self.e['Mouse'].pos[1] * (self.e['Game'].display.get_height() / self.e['Window'].dimensions[1]))

            # clear aim assist log after handling aim but before other entities would fill it again
            self.machines.machines_in_range = []

            self.handle_controller_switch()

            self.camera.update()

            if not self.e['PauseMenu'].paused:
                self.e['EntityGroups'].update()
            self.e['EntityGroups'].renderz(offset=self.camera)

            if not self.e['PauseMenu'].paused:
                self.machines.update()
            else:
                self.machines.paused_update()
            self.machines.render()

            if not self.e['PauseMenu'].paused:
                self.state.update()
            self.state.render()

            self.menus.update()
            self.menus.render()

            self.music.update()

            if not self.e['PauseMenu'].paused:
                self.tilemap.update()
            self.tilemap.render()
            if not self.machines.high_life:
                self.e['Renderer'].renderf(self.gm.update_render, self.e['Window'].dt, offset=self.camera, rot_function=lambda x, y: int((math.sin(x / 100 + time.time() * 1.5) - 0.7) * 30) / 10, z=-5, ignore_tiles=set(self.machines.machine_map))
            else:
                self.hlmap.render()

            self.minimap.update()

            self.transition.update()
            self.transition.render()

            if (not self.player.moved) and (not self.state.title):
                tutorial_img = self.e['Assets'].images['misc']['tutorial']
                if self.e['Window'].time % 1 < 0.7:
                    self.e['Renderer'].blit(tutorial_img, (self.display.get_width() / 2 - tutorial_img.get_width() / 2, self.display.get_height() / 2 - tutorial_img.get_height() / 2 + 50), z=9998, group='ui')
                else:
                    self.e['Renderer'].blit(tutorial_img, (self.display.get_width() / 2 - tutorial_img.get_width() / 2, self.display.get_height() / 2 - tutorial_img.get_height() / 2 + 51), z=9998, group='ui')

            if self.player.dead:
                if self.e['Input'].pressed('restart') or self.e['Controllers'].pressed('interact'):
                    self.restart()

            self.hud.update()
            self.hud.render()

            self.e['Renderer'].cycle({'default': self.display, 'ui': self.hud_surf})

            self.snow.update()
            self.snow.render()

            self.e['Window'].cycle({
                'surface': self.display,
                'hud_surf': self.hud_surf,
                'noise_tex': self.noise_tex,
                'time': self.e['Window'].runtime,
                'scroll': self.camera.int_pos,
                'border_discard': self.e['Window'].border_discard,
                'saturation': self.e['Settings'].saturation,
            })
            
    Game().run()

except Exception as e:
    CRASH_REPORTER.handle_report()
    raise e