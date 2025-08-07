class GameOptions:
    def __init__(self):
        self.music_volume = 0.7
        self.sound_volume = 0.8
        self.fullscreen = False
        self.show_grid = False
        self.auto_save = True
        
    def to_dict(self):
        return {
            "music_volume": self.music_volume,
            "sound_volume": self.sound_volume,
            "fullscreen": self.fullscreen,
            "show_grid": self.show_grid,
            "auto_save": self.auto_save
        }
    
    @classmethod
    def from_dict(cls, data):
        options = cls()
        for key, value in data.items():
            if hasattr(options, key):
                setattr(options, key, value)
        return options