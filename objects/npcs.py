from objects.object_templates import NPC, Node, MapObject, register_node_type
from constants import ObjectState

@register_node_type("ginny")
class Ginny(NPC):
    def update(self, **args):
        super().update(**args)

        match self.state:
            case ObjectState.GINNY_FALLING:
                time = self.engine.event_manager.timer_manager.get_remaining_time(f"event_wait_{self.name}") % 150
                if time > 75:
                    self.engine.sprite_db.get_sprite(self, 0, 2)
                else:
                    self.engine.sprite_db.get_sprite(self, 0, 1)
            case ObjectState.GINNY_FALLEN:
                self.engine.sprite_db.get_sprite(self, 0, 3)
            case ObjectState.GINNY_GET_UP:
                self.engine.sprite_db.get_sprite(self, 0, 4)
            case ObjectState.POSE:
                self.engine.sprite_db.get_sprite(self, 0, 5)
            case ObjectState.TALK:
                self.engine.sprite_db.get_sprite(self, 0, 0)

@register_node_type("maddy")
class Maddy(NPC):
    blush_timer: int = 0
    def update(self, **args):
        super().update(**args)
        match self.state:
            case ObjectState.STAND:
                self.engine.sprite_db.get_sprite(self, 0, 0)
            case ObjectState.BLUSHING:
                num_frames = 4
                self.blush_timer += 1
                if self.blush_timer >= 60:
                    self.blush_timer = 0
                blush_frame = int(num_frames*self.blush_timer/60)
                self.engine.sprite_db.get_sprite(self, 0, 2 + blush_frame)
            case ObjectState.TALK:
                self.engine.sprite_db.get_sprite(self, 0, 1)

@register_node_type("bahati")
class Bahati(NPC):
    evil_timer: int = 0
    def update(self, **args):
        super().update(**args)
        match self.state:
            case ObjectState.TALK:
                self.engine.sprite_db.get_sprite(self, 0, 0)
            case ObjectState.EVIL:
                num_frames = 2
                self.evil_timer += 1
                if self.evil_timer >= 60:
                    self.evil_timer = 0
                blush_frame = int(num_frames*self.evil_timer/60)
                self.engine.sprite_db.get_sprite(self, 0, 3 + blush_frame)
            case ObjectState.POSE:
                self.engine.sprite_db.get_sprite(self, 0, 1)
            case ObjectState.DRAMA:
                self.engine.sprite_db.get_sprite(self, 0, 2)

@register_node_type("imedesinbed")
class ImedesInBed(NPC):
    def update(self, **args):
        super().update(**args)
        match self.state:
            case ObjectState.STAND:
                self.engine.sprite_db.get_sprite(self, new_col = 0)
            case ObjectState.SLEEP:
                self.engine.sprite_db.get_sprite(self, new_col = 1)


