from __future__ import annotations
from typing import Optional

import dgisim.src.state.game_state as gs
from dgisim.src.action import *
import dgisim.src.phase.phase as ph
from dgisim.src.effect.effect import *
from dgisim.src.state.player_state import PlayerState
from dgisim.src.dices import ActualDices


class EndPhase(ph.Phase):
    _CARDS_DRAWN = 2

    def _initialize_end_phase(self, game_state: gs.GameState) -> gs.GameState:
        active_pid = game_state.get_active_player_id()
        effects: list[Effect] = []
        effects += [
            EndPhaseCheckoutEffect(),
            EndRoundEffect(),
            SetBothPlayerPhaseEffect(PlayerState.Act.END_PHASE),
        ]
        return game_state.factory().f_effect_stack(
            lambda es: es.push_many_fl(effects)
        ).f_player(
            active_pid,
            lambda p: p.factory().phase(PlayerState.Act.ACTIVE_WAIT_PHASE).build()
        ).build()

    def _to_roll_phase(self, game_state: gs.GameState, new_round: int) -> gs.GameState:
        active_player_id = game_state.get_active_player_id()
        active_player = game_state.get_player(active_player_id)
        other_player = game_state.get_other_player(active_player_id)
        active_player_deck, new_cards = active_player.get_deck_cards().pick_random_cards(self._CARDS_DRAWN)
        active_player_hand = active_player.get_hand_cards() + new_cards
        other_player_deck, new_cards = other_player.get_deck_cards().pick_random_cards(self._CARDS_DRAWN)
        other_player_hand = other_player.get_hand_cards() + new_cards
        return game_state.factory().round(
            new_round
        ).phase(
            game_state.get_mode().roll_phase()
        ).f_player(
            active_player_id,
            lambda p: p.factory().phase(
                PlayerState.Act.PASSIVE_WAIT_PHASE
            ).dices(
                ActualDices.from_empty()
            ).hand_cards(
                active_player_hand
            ).deck_cards(
                active_player_deck
            ).build()
        ).f_other_player(
            active_player_id,
            lambda p: p.factory().phase(
                PlayerState.Act.PASSIVE_WAIT_PHASE
            ).dices(
                ActualDices.from_empty()
            ).hand_cards(
                other_player_hand
            ).deck_cards(
                other_player_deck
            ).build()
        ).build()

    def _end_both_players(self, game_state: gs.GameState) -> gs.GameState:
        return game_state.factory().f_player1(
            lambda p: p.factory().phase(
                PlayerState.Act.END_PHASE
            ).build()
        ).f_player2(
            lambda p: p.factory().phase(
                PlayerState.Act.END_PHASE
            ).build()
        ).build()

    def _end_game(self, game_state: gs.GameState) -> gs.GameState:
        return game_state.factory().phase(
            game_state.get_mode().game_end_phase()
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
        active_player_id = game_state.get_active_player_id()
        if p1.get_phase() is PlayerState.Act.PASSIVE_WAIT_PHASE and p2.get_phase() is PlayerState.Act.PASSIVE_WAIT_PHASE:
            return self._initialize_end_phase(game_state)
        elif p1.get_phase() is PlayerState.Act.ACTIVE_WAIT_PHASE or p2.get_phase() is PlayerState.Act.ACTIVE_WAIT_PHASE:
            assert self._is_executing_effects(game_state)
            return self._execute_effect(game_state)
        elif p1.get_phase().is_action_phase() or p2.get_phase().is_action_phase():
            # handling death swap
            assert self._is_executing_effects(game_state)
            return self._execute_effect(game_state)
        elif p1.get_phase() is PlayerState.Act.END_PHASE and p2.get_phase() is PlayerState.Act.END_PHASE:
            new_round = game_state.get_round() + 1
            if new_round > game_state.get_mode().round_limit():
                return self._end_game(game_state)
            else:
                return self._to_roll_phase(game_state, new_round)
        raise Exception("Unknown Game State to process")

    def _handle_death_swap_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: DeathSwapAction) -> Optional[gs.GameState]:
        player = game_state.get_player(pid)
        effect_stack = game_state.get_effect_stack()
        # Add Effects
        active_character = player.get_characters().get_active_character()
        assert active_character is not None
        effect_stack = effect_stack.push_one(SwapCharacterEffect(
            StaticTarget(pid, Zone.CHARACTERS, action.selected_character_id)
        ))
        return game_state.factory().effect_stack(
            effect_stack
        ).build()

    def step_action(self, game_state: gs.GameState, pid: gs.GameState.Pid, action: PlayerAction) -> Optional[gs.GameState]:
        effect_stack = game_state.get_effect_stack()
        if effect_stack.is_not_empty() and isinstance(effect_stack.peek(), DeathSwapPhaseStartEffect):
            game_state = game_state.factory().effect_stack(effect_stack.pop()[0]).build()
        if isinstance(action, DeathSwapAction):
            return self._handle_death_swap_action(game_state, pid, action)

        raise NotImplementedError

    def waiting_for(self, game_state: gs.GameState) -> Optional[gs.GameState.Pid]:
        effect_stack = game_state.get_effect_stack()
        # if no effects are to be executed or death swap phase is inserted
        if effect_stack.is_not_empty() \
                and isinstance(effect_stack.peek(), DeathSwapPhaseStartEffect):
            return super().waiting_for(game_state)
        else:
            return None

    def __eq__(self, other: object) -> bool:
        return isinstance(other, EndPhase)

    def __hash__(self) -> int:
        return hash(self.__class__.__name__)
