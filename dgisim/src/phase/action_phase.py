from __future__ import annotations
from typing import Optional, cast

import dgisim.src.state.game_state as gs
import dgisim.src.phase.phase as ph
from dgisim.src.state.player_state import PlayerState
from dgisim.src.action import *
from dgisim.src.event.event import *
from dgisim.src.effect.effect import *


class ActionPhase(ph.Phase):
    def _start_up_phase(self, game_state: gs.GameState) -> gs.GameState:
        # TODO: Handle before action statuses
        active_player_id = game_state.get_active_player_id()
        return game_state.factory().player(
            active_player_id,
            game_state.get_player(active_player_id).factory().phase(
                PlayerState.Act.ACTION_PHASE
            ).build()
        ).build()

    def _to_end_phase(self, game_state: gs.GameState) -> gs.GameState:
        active_player_id = game_state.get_active_player_id()
        return game_state.factory().phase(
            game_state.get_mode().end_phase()
        ).player(
            active_player_id,
            game_state.get_player(active_player_id).factory().phase(
                PlayerState.Act.PASSIVE_WAIT_PHASE
            ).build()
        ).other_player(
            active_player_id,
            game_state.get_other_player(active_player_id).factory().phase(
                PlayerState.Act.PASSIVE_WAIT_PHASE
            ).build()
        ).build()

    def _execute_effect(self, game_state: gs.GameState) -> gs.GameState:
        effect_stack, effect = game_state.get_effect_stack().pop()
        new_game_state = game_state.factory().effect_stack(effect_stack).build()
        if isinstance(effect, DeathSwapPhaseStartEffect):
            print("AFTER DEATH:", new_game_state)
        return effect.execute(new_game_state)

    def _is_executing_effects(self, game_state: gs.GameState) -> bool:
        effect_stack = game_state.get_effect_stack()
        return not effect_stack.is_empty() \
            and not isinstance(effect_stack.peek(), DeathSwapPhaseStartEffect)

    def step(self, game_state: gs.GameState) -> gs.GameState:
        p1 = game_state.get_player1()
        p2 = game_state.get_player2()
        p1p = p1.get_phase()
        p2p = p2.get_phase()
        if p1p is PlayerState.Act.ACTION_PHASE or p2p is PlayerState.Act.ACTION_PHASE:
            assert self._is_executing_effects(game_state)
            return self._execute_effect(game_state)
        elif p1p is PlayerState.Act.PASSIVE_WAIT_PHASE and p2p is PlayerState.Act.PASSIVE_WAIT_PHASE:
            return self._start_up_phase(game_state)
        elif p1p is PlayerState.Act.END_PHASE and p2p is PlayerState.Act.END_PHASE:
            return self._to_end_phase(game_state)
        raise Exception("Unknown Game State to process")

    def _handle_end_round(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: EndRoundAction) -> gs.GameState:
        active_player_id = game_state.get_active_player_id()
        assert active_player_id == pid
        active_player = game_state.get_player(active_player_id)
        other_player = game_state.get_other_player(active_player_id)
        if other_player.get_phase() is PlayerState.Act.END_PHASE:
            other_player_new_phase = PlayerState.Act.END_PHASE
        elif other_player.get_phase() is PlayerState.Act.PASSIVE_WAIT_PHASE:
            other_player_new_phase = PlayerState.Act.ACTION_PHASE
        else:
            print(f"ERROR pid={pid}\n {game_state}")
            raise Exception(f"Unknown Game State to process {other_player.get_phase()}")
        if pid is not active_player_id:
            raise Exception("Unknown Game State to process")
        return game_state.factory().active_player(
            active_player_id.other()
        ).player(
            active_player_id,
            active_player.factory().phase(
                PlayerState.Act.END_PHASE
            ).build()
        ).other_player(
            active_player_id,
            other_player.factory().phase(
                other_player_new_phase
            ).build()
        ).build()

    def _handle_skill_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: SkillAction) -> Optional[gs.GameState]:
        player = game_state.get_player(pid)
        # TODO: check validity of the action
        instruction = action.instruction
        new_effects: list[Effect] = []
        # TODO: put pre checks
        # Costs
        dices = player.get_dices()
        new_dices = dices - action.instruction.dices
        if new_dices is None:
            return None
        # Skill Effect
        active_character = player.get_characters().get_active_character()
        if active_character is None:
            return None
        assert active_character.can_cast_skill()
        # note: it's important to cast skill before new_dices are putted into the game_state
        #       so that normal_attacks can correctly be marked as charged attack
        new_effects += active_character.skill(game_state, action.skill)
        new_effects.append(AllStatusTriggererEffect(
            pid,
            TriggeringSignal.COMBAT_ACTION,
        ))
        new_effects.append(TurnEndEffect())
        # Afterwards
        return game_state.factory().f_effect_stack(
            lambda es: es.push_many_fl(new_effects)
        ).player(
            pid,
            player.factory().dices(new_dices).build()
        ).build()

    def _handle_swap_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: SwapAction) -> Optional[gs.GameState]:
        # Check action validity
        result = game_state.swap_checker().valid_action(pid, action)
        if result is None:
            raise Exception(f"{action} from {pid} is invalid for gamestate:\n{game_state}")
        game_state, action_speed = result

        player = game_state.get_player(pid)
        new_effects: list[Effect] = []

        # Costs
        new_dices = player.get_dices() - action.instruction.dices
        assert new_dices.is_legal()

        # Add Effects
        active_character = player.get_characters().get_active_character()
        assert active_character is not None
        new_effects.append(SwapCharacterEffect(
            StaticTarget(pid, Zone.CHARACTER, action.selected_character_id)
        ))

        if action_speed is EventSpeed.COMBAT_ACTION:
            new_effects.append(
                AllStatusTriggererEffect(
                    pid=pid,
                    signal=TriggeringSignal.COMBAT_ACTION,
                )
            )
            new_effects.append(TurnEndEffect())
        elif action_speed is EventSpeed.FAST_ACTION:
            new_effects.append(
                AllStatusTriggererEffect(
                    pid=pid,
                    signal=TriggeringSignal.FAST_ACTION,
                )
            )

        return game_state.factory().effect_stack(
            game_state.get_effect_stack().push_many_fl(new_effects)
        ).player(
            pid,
            player.factory().dices(new_dices).build()
        ).build()

    def _handle_card_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: CardAction) -> Optional[gs.GameState]:
        paid_dices = action.instruction.dices
        card = action.card

        # verify card usage validity
        if not card.usable(game_state, pid):
            raise Exception(f"{card.name()} is not usable for {pid}"
                            + f"in game state:\n{game_state}")

        # verify action validity
        if not card.valid_instruction(game_state, pid, action.instruction):
            raise Exception(f"{action.instruction} is not valid of the {card.name()}"
                            + f"in the game state:\n{game_state}")

        #  setup
        player = game_state.get_player(pid)
        new_effects: list[Effect] = []

        # Costs
        dices = player.get_dices()
        new_dices = dices - paid_dices
        if not new_dices.is_legal():
            print(f"Fail with new dices: <{new_dices}> for card: {card.name()}")
            assert False

        # Card
        new_effects.append(RemoveCardEffect(pid, card))
        new_effects += card.effects(game_state, pid, action.instruction)
        if card.is_combat_action():
            new_effects.append(AllStatusTriggererEffect(
                pid,
                TriggeringSignal.COMBAT_ACTION,
            ))
            new_effects.append(TurnEndEffect())
        return game_state.factory().f_effect_stack(
            lambda es: es.push_many_fl(new_effects)
        ).player(
            pid,
            player.factory().dices(new_dices).build()
        ).build()

    def _handle_death_swap_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: DeathSwapAction) -> Optional[gs.GameState]:
        # Check action validity
        result = game_state.swap_checker().valid_action(pid, action)
        if result is None:
            raise Exception(f"{action} from {pid} is invalid for gamestate:\n{game_state}")
        game_state, _ = result
        
        game_state = game_state.factory().f_effect_stack(lambda es: es.pop()[0]).build()
        player = game_state.get_player(pid)
        effect_stack = game_state.get_effect_stack()
        # Add Effects
        active_character = player.get_characters().get_active_character()
        assert active_character is not None
        effect_stack = effect_stack.push_one(SwapCharacterEffect(
            StaticTarget(pid, Zone.CHARACTER, action.selected_character_id)
        ))
        return game_state.factory().effect_stack(
            effect_stack
        ).build()

    def _handle_game_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: GameAction) -> Optional[gs.GameState]:
        player = game_state.get_player(pid)
        if isinstance(action, SkillAction):
            action = cast(SkillAction, action)
            return self._handle_skill_action(game_state, pid, action)
        elif isinstance(action, SwapAction):
            action = cast(SwapAction, action)
            return self._handle_swap_action(game_state, pid, action)
        elif isinstance(action, CardAction):
            action = cast(CardAction, action)
            return self._handle_card_action(game_state, pid, action)
        elif isinstance(action, DeathSwapAction):
            action = cast(DeathSwapAction, action)
            return self._handle_death_swap_action(game_state, pid, action)
        raise Exception("Unhandld action", action)

    def step_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: PlayerAction) -> Optional[gs.GameState]:
        # check action arrived at the right state
        if pid is not self.waiting_for(game_state):
            raise Exception(f"Unexpected action from {pid} at game state:\n{game_state}")

        # check death swap phase
        effect_stack = game_state.get_effect_stack()
        if effect_stack.is_not_empty() and isinstance(effect_stack.peek(), DeathSwapPhaseStartEffect):
            if not isinstance(action, DeathSwapAction):
                raise Exception(f"Trying to execute {action} when a death swap is expected")
            # game_state = game_state.factory().effect_stack(effect_stack.pop()[0]).build()

        if isinstance(action, GameAction):
            action = cast(GameAction, action)
            return self._handle_game_action(game_state, pid, action)
        elif isinstance(action, EndRoundAction):
            action = cast(EndRoundAction, action)
            return self._handle_end_round(game_state, pid, action)
        raise Exception("Unknown Game State to process")

    def waiting_for(self, game_state: gs.GameState) -> Optional[gs.GameState.Pid]:
        effect_stack = game_state.get_effect_stack()
        # if no effects are to be executed or death swap phase is inserted
        if effect_stack.is_empty() \
                or isinstance(effect_stack.peek(), DeathSwapPhaseStartEffect):
            return super().waiting_for(game_state)
        else:
            return None

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ActionPhase)

    def __hash__(self) -> int:
        return hash(self.__class__.__name__)
