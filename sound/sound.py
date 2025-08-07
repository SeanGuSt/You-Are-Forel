import pygame
import os
from constants import SOUNDS_DIR

pygame.mixer.init()

class SoundDatabase:
    def __init__(self):
        self.sound = {}
        fs_folder = os.path.join(SOUNDS_DIR, "footsteps")
        onlyfiles = [f for f in os.listdir(fs_folder) if os.path.isfile(os.path.join(fs_folder, f))]
        for file_name in onlyfiles:
            if file_name.endswith(".wav"):
                self.sound[file_name[:-4]] = pygame.mixer.Sound(os.path.join(fs_folder, file_name))
