import time
import os
import socket
import platform

from scripts import pygpen as pp

from .util import CONTROLLER_MAPPING_SWAPPED, CONTROLLER_MAPPING

DEFAULT_SETTINGS = {
    'fps_cap': '165',
    'master_volume': '100%',
    'sfx_volume': '100%',
    'music_volume': '100%',
    'fullscreen': 'disabled',
    'aim_assist': '100%',
    'windowed_resolution': 'native',
    'outline': 'enabled',
    'show_fps': 'disabled',
    'swap_trigger_bumper': 'disabled',
    'pink_player': 'disabled',
    'saturation': '100%',
}

class Settings(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        if not os.path.isdir('save'):
            os.mkdir('save')

        if not os.path.isdir('settings'):
            os.mkdir('settings')
        
        if not os.path.exists('save/save.json'):
            default_save = {
                'best_score': 0,
                'weapon_enchants': {},
            }

            pp.utils.io.write_json('save/save.json', default_save)

        try:
            self.settings_save = pp.utils.io.read_json('settings/settings.json')
            for field in DEFAULT_SETTINGS:
                if field not in self.settings_save:
                    self.settings_save[field] = DEFAULT_SETTINGS[field]
        except FileNotFoundError:
            initial_resolution = 'native'
            # setting the windowed resolution to the display resolution doesn't emulate fullscreen on all linux distros
            # however, defaulting to native on steamdeck is ideal
            if (platform.system().lower() == 'linux') and (not self.steamdeck):
                initial_resolution = '1152x648'

            new_settings = DEFAULT_SETTINGS.copy()
            new_settings['windowed_resolution'] = initial_resolution

            self.settings_save = new_settings
            self.save()

    def save(self):
        pp.utils.io.write_json('settings/settings.json', self.settings_save)

    def setting(self, field):
        return self.settings_save[field] if field in self.settings_save else None
    
    @property
    def steamdeck(self):
        return socket.gethostname() == 'steamdeck'
    
    @property
    def sfx_volume(self):
        return int(self.settings_save['sfx_volume'][:-1]) * 0.01 * int(self.settings_save['master_volume'][:-1]) * 0.01

    @property
    def music_volume(self):
        return int(self.settings_save['music_volume'][:-1]) * 0.01 * int(self.settings_save['master_volume'][:-1]) * 0.01
    
    @property
    def saturation(self):
        return int(self.settings_save['saturation'][:-1]) * 0.01
    
    @property
    def fullscreen(self):
        return self.settings_save['fullscreen'] == 'enabled'
    
    @property
    def aim_assist(self):
        return int(self.settings_save['aim_assist'][:-1]) * 0.01
    
    @property
    def resolution(self):
        try:
            return tuple(int(v) for v in self.settings_save['windowed_resolution'].split('x'))
        except ValueError:
            return None
    
    def update(self, field, value):
        self.settings_save[field] = value
        self.save()

        if field == 'swap_trigger_bumper':
            self.e['Controllers'].update_mappings(CONTROLLER_MAPPING_SWAPPED if value == 'enabled' else CONTROLLER_MAPPING)
        if field == 'fps_cap':
            try:
                self.e['Window'].fps_cap = int(value)
            except ValueError:
                self.e['Window'].fps_cap = 9999
        if field in {'sfx_volume', 'master_volume'}:
            self.e['Sounds'].sounds['ambience'].set_volume(self.sfx_volume * 0.6)
        if field == 'windowed_resolution':
            self.e['Window'].reload_display(self.resolution)
        if field == 'fullscreen':
            size = self.e['Window'].dimensions
            if self.fullscreen:
                size = (0, 0)
            else:
                size = self.resolution
            self.e['Window'].reload_display(size)

            # sometimes I just get a black screen from going straigh to fullscreen once
            # double toggling seems to fix this issue
            if self.fullscreen:
                self.settings_save['fullscreen'] = 'disabled'
                self.e['Window'].reload_display(size)
                self.settings_save['fullscreen'] = 'enabled'
                self.e['Window'].reload_display(size)
            