from __future__ import annotations
from typing_extensions import override
from dataclasses import dataclass, fields

from dgisim.src.card.cards import Cards
from dgisim.src.dices import ActualDices
from dgisim.src.effect.effect import StaticTarget
from dgisim.src.character.character_skill_enum import CharacterSkill
import dgisim.src.state.game_state as gs


@dataclass(frozen=True)
class PlayerAction:
    def __str__(self) -> str:
        cls_fields = fields(self)
        paired_fields = (f"{field.name}={str(self.__getattribute__(field.name))}" for field in cls_fields)
        return f"{self.__class__.__name__}:({', '.join(paired_fields)})"


@dataclass(frozen=True)
class CardSelectAction(PlayerAction):
    selected_cards: Cards

    def num_cards(self) -> int:
        return self.selected_cards.num_cards()

    def __str__(self) -> str:
        name = self.__class__.__name__
        cards = '; '.join(str(self.selected_cards).split('\n'))
        return f"{name}[{cards}]"


@dataclass(frozen=True)
class CharacterSelectAction(PlayerAction):
    selected_character_id: int


@dataclass(frozen=True)
class EndRoundAction(PlayerAction):
    pass


@dataclass(frozen=True)
class GameAction(PlayerAction):
    def is_valid_action(self, game_state: gs.GameState) -> bool:
        raise Exception("Not overriden")


@dataclass(frozen=True)
class CardAction(GameAction):
    from dgisim.src.card.card import Card
    card: type[Card]
    instruction: Instruction

    def __str__(self) -> str:
        return f"<{self.card.__name__}, {self.instruction}>"


@dataclass(frozen=True)
class SkillAction(GameAction):
    skill: CharacterSkill
    instruction: DiceOnlyInstruction

    def __str__(self) -> str:
        return f"<{self.skill}, {self.instruction}>"


@dataclass(frozen=True)
class SwapAction(GameAction):
    selected_character_id: int
    instruction: Instruction


@dataclass(frozen=True)
class DeathSwapAction(GameAction):
    selected_character_id: int


@dataclass(frozen=True, kw_only=True)
class Instruction:
    dices: ActualDices

    def __str__(self) -> str:
        cls_fields = fields(self)
        paired_fields = (f"{field.name}={str(self.__getattribute__(field.name))}" for field in cls_fields)
        return f"{self.__class__.__name__}:({', '.join(paired_fields)})"


@dataclass(frozen=True, kw_only=True)
class DiceOnlyInstruction(Instruction):
    pass


@dataclass(frozen=True, kw_only=True)
class CharacterTargetInstruction(Instruction):
    target: StaticTarget

@dataclass(frozen=True, kw_only=True)
class ReplaceSupportInstruction(Instruction):
    target: StaticTarget


@dataclass(frozen=True, kw_only=True)
class SourceTargetInstruction(Instruction):
    source: StaticTarget
    target: StaticTarget
