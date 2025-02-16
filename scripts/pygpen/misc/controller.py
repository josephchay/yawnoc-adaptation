import platform
import math

import pygame

from ..utils.elements import ElementSingleton
from ..utils.io import read_f

import pygame._sdl2.controller

CONTROLLER_INPUT_IDS = {
    'back': (pygame.CONTROLLER_BUTTON_BACK, 'button'),
    'leftx': (pygame.CONTROLLER_AXIS_LEFTX, 'axis'),
    'lefty': (pygame.CONTROLLER_AXIS_LEFTY, 'axis'),
    'rightx': (pygame.CONTROLLER_AXIS_RIGHTX, 'axis'),
    'righty': (pygame.CONTROLLER_AXIS_RIGHTY, 'axis'),
    'leftshoulder': (pygame.CONTROLLER_BUTTON_LEFTSHOULDER, 'button'),
    'rightshoulder': (pygame.CONTROLLER_BUTTON_RIGHTSHOULDER, 'button'),
    'lefttrigger': (pygame.CONTROLLER_AXIS_TRIGGERLEFT, 'axis'),
    'righttrigger': (pygame.CONTROLLER_AXIS_TRIGGERRIGHT, 'axis'),
    'a': (pygame.CONTROLLER_BUTTON_A, 'button'),
    'b': (pygame.CONTROLLER_BUTTON_B, 'button'),
}

PLATFORM_RAW = platform.system().lower()
PLATFORM = 'Linux'
if PLATFORM_RAW == 'windows':
    PLATFORM = 'Windows'
if PLATFORM_RAW == 'darwin':
    PLATFORM = 'Mac OS X'

AXIS_PRESS_THRESHOLD = 0.5

STICK_CAP = 0.9
STICK_DEAD_ZONE = 0.2

class SDL2Binding:
    def __init__(self, controller, binding):
        self.controller = controller
        self.binding = binding
        self.id = CONTROLLER_INPUT_IDS[self.binding][0]
        self.type = CONTROLLER_INPUT_IDS[self.binding][1]

        self.pressed = False
        self.pressed_neg = False
        self.released = False
        self.released_neg = False
        self.holding = False
        self.holding_neg = False

        # load holding state so that pressed states don't get retriggered from reloading bindings
        self.raw = self.read()
        pressed_reading = self.raw > AXIS_PRESS_THRESHOLD
        pressed_neg_reading = self.raw < -AXIS_PRESS_THRESHOLD
        self.holding = pressed_reading
        self.holding_neg = pressed_neg_reading
    
    def read(self):
        if self.type == 'button':
            return self.controller.get_button(self.id)
        if self.type == 'axis':
            return self.controller.get_axis(self.id) / 32768
        return 0
    
    def update(self):
        self.pressed = False
        self.pressed_neg = False
        self.released = False
        self.released_neg = False
        self.raw = self.read()
        pressed_reading = self.raw > AXIS_PRESS_THRESHOLD
        pressed_neg_reading = self.raw < -AXIS_PRESS_THRESHOLD
        if pressed_reading and not self.holding:
            self.pressed = True
        if not pressed_reading and self.holding:
            self.released = True
        if pressed_neg_reading and not self.holding_neg:
            self.pressed_neg = True
        if not pressed_neg_reading and self.holding_neg:
            self.released_neg = True
        self.holding = pressed_reading
        self.holding_neg = pressed_neg_reading


class Controller:
    def __init__(self, parent, joystick):
        self.parent = parent
        self.joystick = joystick
        self.controller = pygame._sdl2.controller.Controller.from_joystick(joystick)

        self.guid = self.joystick.get_guid()

        self.reload_bindings()

    @property
    def name(self):
        return self.controller.name
    
    def reload_bindings(self):
        self.bindings = {self.parent.name_mapping[key]: SDL2Binding(self.controller, key) for key in self.parent.name_mapping}

    def update(self):
        for binding in self.bindings.values():
            binding.update()

    def read_stick(self, x_axis, y_axis):
        state = [0, 0]

        # assuming that the controller axes are physically limited to circular ranges (making (1, 1) impossible)
        reading = (min(1, max(-1, self.raw(x_axis) / STICK_CAP)), min(1, max(-1, self.raw(y_axis) / STICK_CAP)))
        if any([abs(v) > STICK_DEAD_ZONE for v in reading]):
            angle = math.atan2(reading[1], reading[0])
            amount = min(1, max(-1, math.sqrt(self.raw(x_axis) ** 2 + self.raw(y_axis) ** 2) / STICK_CAP))
            state = [math.cos(angle) * amount, math.sin(angle) * amount]
        return state
    
    def consume(self, key):
        if key in self.bindings:
            self.bindings[key].pressed = False
            self.bindings[key].released = False
            self.bindings[key].pressed_neg = False
            self.bindings[key].released_neg = False

    def pressed(self, key):
        if key in self.bindings:
            return self.bindings[key].pressed
        
    def released(self, key):
        if key in self.bindings:
            return self.bindings[key].released
        
    def holding(self, key):
        if key in self.bindings:
            return self.bindings[key].holding
        
    def pressed_neg(self, key):
        if key in self.bindings:
            return self.bindings[key].pressed_neg
        
    def released_neg(self, key):
        if key in self.bindings:
            return self.bindings[key].released_neg
        
    def holding_neg(self, key):
        if key in self.bindings:
            return self.bindings[key].holding_neg
        
    def raw(self, key):
        if key in self.bindings:
            return self.bindings[key].raw

class Controllers(ElementSingleton):
    def __init__(self, name_mapping={}, base_path='.'):
        super().__init__()

        self.name_mapping = name_mapping
        self.base_path = base_path

        self.controllers = {}
        self.last = None

        pygame._sdl2.controller.init()

    @property
    def name(self):
        if self.last:
            return self.last.name
        
    def update_mappings(self, mapping):
        self.name_mapping = mapping

        for controller in self.controllers.values():
            controller.reload_bindings()
        
    def consume(self, key):
        if self.last:
            self.last.consume(key)
        
    def read_stick(self, x_axis, y_axis):
        if self.last:
            return self.last.read_stick(x_axis, y_axis)
        return [0, 0]

    def pressed(self, key):
        if self.last:
            return self.last.pressed(key)
        
    def released(self, key):
        if self.last:
            return self.last.released(key)
        
    def holding(self, key):
        if self.last:
            return self.last.holding(key)
        
    def pressed_neg(self, key):
        if self.last:
            return self.last.pressed_neg(key)
        
    def released_neg(self, key):
        if self.last:
            return self.last.released_neg(key)
        
    def holding_neg(self, key):
        if self.last:
            return self.last.holding_neg(key)
        
    def raw(self, key):
        if self.last:
            return self.last.raw(key)

    def add(self, event):
        joystick = pygame.joystick.Joystick(event.device_index)
        new_controller = Controller(self, joystick)
        self.controllers[joystick.get_instance_id()] = new_controller
        self.last = new_controller

    def remove(self, event):
        if event.instance_id in self.controllers:
            del self.controllers[event.instance_id]
            if len(self.controllers):
                self.last = self.controllers[list(self.controllers)[-1]]
            else:
                self.last = None

    def update(self):
        for controller in self.controllers.values():
            controller.update()