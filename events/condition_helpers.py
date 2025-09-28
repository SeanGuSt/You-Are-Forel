from typing import TYPE_CHECKING
from objects.characters import Party, Character
from objects.object_templates import Node
from quests.quests import Quest, QuestLog, QuestStep
from constants import Direction
condition_funcs = {}

def condition(key):
    def decorator(func):
        condition_funcs[key] = func
        return func
    return decorator

@condition("last_dialog")
def last_dialog(last_input: str, line: str, true_if: bool):
    return (last_input in line.split("|")) == true_if

@condition("talked")
def talked(dialog_key: str, talked_to_npcs: set, true_if: bool):
    return (dialog_key in talked_to_npcs) == true_if

@condition("have_item")
def have_item(party: Party, line: str, true_if: bool):
    for item in party.inventory:
        if item.item_id == line:
            return true_if
    for member in party.members:
        for equipment in member.equipped.values():
            if equipment and equipment.item_id == line:
                return true_if
    return not true_if

@condition("have_quest")
def have_quest(quest: Quest, true_if: bool):
    return (quest and quest.started) == true_if

@condition("mid_quest")
def mid_quest(quest: Quest, true_if: bool):
    if quest:
        return quest.started == true_if and (quest.completed | quest.failed) != true_if
    return not true_if

@condition("finished_quest")
def finished_quest(quest: Quest, true_if: bool):
    if quest:
        return (quest.completed | quest.failed) == true_if
    return not true_if

@condition("completed_quest")
def completed_quest(quest: Quest, true_if: bool):
    if quest:
        return quest.completed == true_if
    return not true_if

@condition("failed_quest")
def failed_quest(quest: Quest, true_if: bool):
    if quest:
        return quest.failed == true_if
    return not true_if

@condition("have_quest_step")
def have_quest_step(quest: Quest, step_name: str, true_if: bool):
    if quest:
        quest_step = quest.steps.get(step_name, None)
        if quest_step:
            return quest_step.started == true_if
    return not true_if

@condition("mid_quest_step")
def mid_quest_step(quest: Quest, step_name: str, true_if: bool):
    if quest:
        quest_step = quest.steps.get(step_name, None)
        if quest_step:
            return quest_step.started == true_if and (quest_step.completed | quest_step.failed) != true_if
    return not true_if

@condition("finished_quest_step")
def finished_quest_step(quest: Quest, step_name: str, true_if: bool):
    if quest:
        quest_step = quest.steps.get(step_name, None)
        if quest_step:
            return (quest_step.completed | quest_step.failed) == true_if
    return not true_if

@condition("completed_quest_step")
def completed_quest_step(quest: Quest, step_name: str, true_if: bool):
    if quest:
        quest_step = quest.steps.get(step_name, None)
        if quest_step:
            return quest_step.completed == true_if
    return not true_if

@condition("failed_quest_step")
def failed_quest_step(quest: Quest, step_name: str, true_if: bool):
    if quest:
        quest_step = quest.steps.get(step_name, None)
        if quest_step:
            return quest_step.failed == true_if
    return not true_if

@condition("leader_wear")
def leader_wear(leader: Character, line: str, true_if: bool):
    if "none" in line:
        if leader.equipped[line.split("_")[0]]:
            return not true_if
        return true_if
    for item in leader.equipped.values():
        if item and item.item_id in line.split("|"):
            return true_if
    return not true_if

@condition("leader_direction")
def leader_direction(leader: Character, reference: Node, direction: Direction, true_if: bool):
    diff = reference.subtract_tuples(leader.position, reference.position)
    return (reference.get_sign(diff)==direction.value)==true_if
    #return (leader.position == reference.add_tuples(reference.position, direction.value)) == true_if

@condition("in_party")
def in_party(party: Party, name: str, true_if: bool):
    for party_member in party.members:
        if party_member.name == name:
            return true_if
    return not true_if

@condition("party_count")
def party_count(party: Party, count: int, true_if: bool):
    return (len(party.members)==count)==true_if