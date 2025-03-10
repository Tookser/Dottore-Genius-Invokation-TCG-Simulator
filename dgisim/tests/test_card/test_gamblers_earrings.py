import unittest

from .common_imports import *


class TestGamblersEarrings(unittest.TestCase):
    def test_gamblers_earrings(self):
        base_game = ACTION_TEMPLATE.factory().f_player1(
            lambda p1: p1.factory().f_characters(
                lambda cs: cs.factory().active_character_id(
                    3
                ).f_active_character(
                    lambda ac: ac.factory().energy(
                        ac.get_max_energy()
                    ).build()
                ).build()  # Keqing
            ).f_hand_cards(
                lambda hcs: hcs.add(GamblersEarrings).add(GamblersEarrings).add(GamblersEarrings)
            ).build()
        ).f_player2(
            lambda p2: p2.factory().phase(
                Act.END_PHASE
            ).f_combat_statuses(
                lambda cstts: cstts.update_status(IcicleStatus())  # Kaeya's burst
            ).build()
        ).build()
        base_game = kill_character(base_game, character_id=1, hp=1)
        base_game = kill_character(base_game, character_id=2, hp=1)
        for i in range(1, 4):
            base_game = just(base_game.action_step(Pid.P1, CardAction(
                card=GamblersEarrings,
                instruction=StaticTargetInstruction(
                    dices=ActualDices({Element.OMNI: 1}),
                    target=StaticTarget(Pid.P1, Zone.CHARACTERS, i)
                )
            )))
            base_game = auto_step(base_game)
        assert isinstance(base_game.get_player1().just_get_active_character(), Keqing)
        p1ac = base_game.get_player1().just_get_active_character()
        self.assertIn(GamblersEarringsStatus, p1ac.get_equipment_statuses())
        gamblers = p1ac.get_equipment_statuses().just_find(GamblersEarringsStatus)
        self.assertEqual(gamblers.informed_num, 0)
        self.assertEqual(gamblers.triggered_num, 0)

        # overloaded kill checks swaps before triggering gamblers earrings
        game_state = oppo_aura_elem(base_game, Element.PYRO)
        game_state = just(game_state.action_step(
            Pid.P1,
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_SKILL1,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3}))
            )
        ))
        num_dices = game_state.get_player1().get_dices().num_dices()
        gsm = GameStateMachine(game_state, LazyAgent(), LazyAgent())
        gsm.step_until_holds(
            lambda gs:
            gs.get_player1().just_get_active_character().get_elemental_aura().contains(Element.CRYO)
        )
        self.assertEqual(gsm.get_game_state().get_player1().get_dices().num_dices(), num_dices)

        gsm.auto_step(observe=False)
        self.assertEqual(gsm.get_game_state().get_player1().get_dices().num_dices(), num_dices + 2)

        # multiple kill rewards correctly
        game_state = oppo_aura_elem(base_game, Element.PYRO)  # overload, so P2 doesn't need to swap
        game_state = just(game_state.action_step(
            Pid.P1,
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_BURST,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 4}))
            )
        ))
        num_dices = game_state.get_player1().get_dices().num_dices()
        gsm = GameStateMachine(game_state, LazyAgent(), LazyAgent())
        gsm.auto_step(observe=False)
        self.assertEqual(gsm.get_game_state().get_player1().get_dices().num_dices(), num_dices + 4)
