import pygame
import json
import os
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from constants import QUEST_DIR
if TYPE_CHECKING:
    from ultimalike import GameEngine

@dataclass
class QuestStep:
    name: str
    description: str
    description_vague: str = ""
    description_failed: str = ""
    description_completed: str = ""
    started: bool = False
    failed: bool = False
    completed: bool = False
    def update_completion_from_save(self, save_dict):
        if "started" not in save_dict:
            return
        self.started = save_dict["started"]
        self.failed = save_dict["failed"]
        self.completed = save_dict["completed"]
    def to_dict(self):
        if any([self.started, self.failed, self.completed]):
            return {"started" : self.started, "failed" : self.failed, "completed" : self.completed}
        return {}
    @classmethod
    def from_dict(cls, data):
        return cls(**data)

@dataclass
class Quest(QuestStep):
    reward: dict[str, str] = field(default_factory=lambda: {})
    steps: dict[str, QuestStep] = field(default_factory=lambda: {})
    hints: dict[str, QuestStep] = field(default_factory=lambda: {})
    def to_dict(self):
        quest = super().to_dict()
        if self.steps:
            quest["steps"] = {}
            for step_id, step in self.steps.items():
                quest["steps"][step_id] = step.to_dict()
        if self.hints:
            quest["hints"] = {}
            for hint_id, hint in self.hints.items():
                quest["hints"][hint_id] = hint.to_dict()
        return quest

    @classmethod
    def from_dict(cls, data):
        quest = cls(**data)
        for key, step in quest.steps.items():
            quest.steps[key] = QuestStep.from_dict(step)
        for key, hint in quest.hints.items():
            quest.hints[key] = QuestStep.from_dict(hint)
        return quest

class QuestLog:
    def __init__(self, engine: 'GameEngine'):
        self.quests: dict[str, Quest] = {}
        self.load_quests()
        self.engine = engine
    
    def load_quests(self):
        onlyfiles = [f for f in os.listdir(QUEST_DIR) if os.path.isfile(os.path.join(QUEST_DIR, f))]
        for file_name in onlyfiles:
            if file_name.endswith("quest.json"):
                with open(os.path.join(QUEST_DIR, file_name), 'r') as f:
                    quests = json.load(f)
                    if quests:
                        for key, value in quests.items():
                            self.quests[key] = Quest.from_dict(value)
    
    def start_quest(self, quest: str):
        if quest in self.quests:
            self.quests[quest].started = True
        return quest

    def finish_quest(self, quest_name: str, did_succeed: bool = True):
        if quest_name in self.quests:
            quest = self.quests[quest_name]
            if did_succeed:
                quest.started = True #This way players can finish a quest without even having it yet.
                quest.completed = True
            else:
                quest.failed = True #But if they fail a quest before starting it, they don't get to know :P
            return quest

    def reveal_quest_step(self, quest_step: str):
        if "__" in quest_step:
            quest_name, step_name = quest_step.split("__")
            if quest_name in self.quests:
                quest = self.quests[quest_name]
                if step_name in quest.steps:
                    step = quest.steps[step_name]
                    step.started = True #Since quest steps won't show up until the quest itself is started, it's fine to show this.


    def finish_quest_step(self, quest_step: str, did_succeed: bool = True):
        if "__" in quest_step:
            quest_name, step_name = quest_step.split("__")
            if quest_name in self.quests:
                quest = self.quests[quest_name]
                if step_name in quest.steps:
                    step = quest.steps[step_name]
                    step.started = True #Since quest steps won't show up until the quest itself is started, it's fine to show this.
                    if did_succeed:
                        step.completed = True
                    else:
                        step.failed = True

    def reveal_quest_hint(self, quest_hint: str):#Quest hints will also be QuestStep objects. We just choose to ignore the completed/failed attributes
        if "__" in quest_hint:
            quest_name, hint_name = quest_hint.split("__")
            if quest_name in self.quests:
                quest = self.quests[quest_name]
                if hint_name in quest.hints:
                    hint = quest.hints[hint_name]
                    hint.started = True
    
    def save_quests(self):
        q_dict = {}
        for key, quest in self.quests.items():
            q_dict[key] = quest.to_dict()
        print(q_dict)
        return q_dict
    
    def load_quests_from_save(self, quest_saves: dict):
        for key, quest in quest_saves.items():
            if key in self.quests:
                self.quests[key].update_completion_from_save(quest)
            for key2, step in quest.get("steps", {}).items():
                if key2 in self.quests[key].steps:
                    self.quests[key].steps[key2].update_completion_from_save(step)
            for key2, hint in quest.get("hints", {}).items():
                if key2 in self.quests[key].hints:
                    self.quests[key].hints[key2].update_completion_from_save(hint)

