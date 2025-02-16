import pygame

from scripts import pygpen as pp

TRACK_VOLUMES = {
    'summer_battle': 0.3,
    'summer_shop': 0.3,
    'fall_shop': 0.6,
    'highlife': 0.5,
}

TRACK_LENGTHS = {
    'summer_battle': 96,
    'summer_shop': 123,
    'fall_shop': 96,
    'highlife': 22,
}

class Music(pp.ElementSingleton):
    def __init__(self):
        super().__init__()

        self.fading = [0, 0]
        self.last_volume = 1.0

    def update(self):
        if self.fading[0]:
            self.fading[0] = max(0, self.fading[0] - self.e['Window'].dt)
            pygame.mixer.music.set_volume(self.last_volume * (self.fading[0] / self.fading[1])) 

    def play(self, track, start=0, fadein=0):
        self.fading = [0, 0]
        start = start % TRACK_LENGTHS[track]
        pygame.mixer.music.load(f'data/music/{track}.wav')
        self.last_volume = TRACK_VOLUMES[track] * self.e['Settings'].music_volume
        pygame.mixer.music.set_volume(self.last_volume)
        pygame.mixer.music.play(-1, start=start, fade_ms=int(fadein * 1000))

    def fadeout(self, duration):
        self.fading = [duration, duration]