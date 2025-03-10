import unittest

from dgisim.tests.test_card.common_imports import *


class TestKnightsOfFavoniusLibrary(unittest.TestCase):
    def test_knights_of_favonius_library(self):
        base_game = ACTION_TEMPLATE.factory().f_player1(
            lambda p: p.factory().hand_cards(
                Cards({
                    KnightsOfFavoniusLibrary: 2,
                })
            ).build()
        ).f_player2(
            lambda p: p.factory().hand_cards(
                Cards({
                    KnightsOfFavoniusLibrary: 2,
                })
            ).build()
        ).build()

        a1, a2 = PuppetAgent(), PuppetAgent()
        gsm = GameStateMachine(base_game, a1, a2)
        a1.inject_actions([
            CardAction(
                card=KnightsOfFavoniusLibrary,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.ANEMO: 1})),
            ),
            DicesSelectAction(
                selected_dices=ActualDices({}),
            ),
            EndRoundAction(),
        ])
        a2.inject_actions([
            CardAction(
                card=KnightsOfFavoniusLibrary,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.PYRO: 1})),
            ),
            DicesSelectAction(
                selected_dices=ActualDices({}),
            ),
            CardAction(
                card=KnightsOfFavoniusLibrary,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.ELECTRO: 1})),
            ),
            DicesSelectAction(
                selected_dices=ActualDices({Element.GEO: 2}),
            ),
            EndRoundAction(),
        ])
        gsm.step_until_phase(base_game.get_mode().roll_phase())
        gsm.auto_step()
        game_state = gsm.get_game_state()
        p1, p2 = game_state.get_player1(), game_state.get_player2()
        self.assertEqual(p1.get_dice_reroll_chances(), 2)
        self.assertEqual(p2.get_dice_reroll_chances(), 3)
        self.assertIn(KnightsOfFavoniusLibrarySupport, p1.get_supports())
        self.assertIn(KnightsOfFavoniusLibrarySupport, p2.get_supports())