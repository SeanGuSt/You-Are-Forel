import pygame

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultimalike import GameEngine
def quest_log_inputs(self: 'GameEngine', event):
    quest_log = self.quest_log
    selected_indices = self.selected_quest_indices
    current_focus = self.current_quest_focus

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            self.revert_state()
        quests = [q for q in quest_log.quests.values() if q.started]
        if not quests:
            return  # Nothing to do
        quest = quests[selected_indices[0]]
        if event.key == pygame.K_TAB:
            self.current_quest_focus = (current_focus + 1) % 3

        elif event.key == pygame.K_UP:
            selected_indices[current_focus] = max(0, selected_indices[current_focus] - 1)

        elif event.key == pygame.K_DOWN:
            if current_focus == 0:
                selected_indices[0] = min(len(quests) - 1, selected_indices[0] + 1)
                selected_indices[1] = 0  # Reset steps
                selected_indices[2] = 0  # Reset hints
            elif current_focus == 1:
                steps = list(quest.steps.values())
                selected_indices[1] = min(len(steps) - 1, selected_indices[1] + 1)
            elif current_focus == 2:
                hints = list(quest.hints.values())
                selected_indices[2] = min(len(hints) - 1, selected_indices[2] + 1)

    return current_focus
