import unittest

from dgisim.tests.test_characters.common_imports import *


class TestKeqing(unittest.TestCase):
    BASE_GAME = ACTION_TEMPLATE.factory().f_player1(
        lambda p: p.factory().f_characters(
            lambda cs: cs.factory().active_character_id(3).build()  # make active character Keqing
        ).f_hand_cards(
            lambda hcs: hcs.add(ThunderingPenance)
        ).build()
    ).f_player2(
        lambda p: p.factory().phase(Act.END_PHASE).build()
    ).build()
    assert type(BASE_GAME.get_player1().just_get_active_character()) is Keqing

    def test_normal_attack(self):
        a1, a2 = PuppetAgent(), PuppetAgent()
        gsm = GameStateMachine(self.BASE_GAME, a1, a2)
        a1.inject_action(SkillAction(
            skill=CharacterSkill.NORMAL_ATTACK,
            instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
        ))
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 10)

        gsm.player_step()
        gsm.auto_step()
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 8)
        self.assertFalse(p2ac.get_elemental_aura().elem_auras())

    def test_elemental_skill1(self):
        a1, a2 = PuppetAgent(), PuppetAgent()
        gsm = GameStateMachine(self.BASE_GAME, a1, a2)
        a1.inject_action(SkillAction(
            skill=CharacterSkill.ELEMENTAL_SKILL1,
            instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
        ))
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 10)

        # first skill
        gsm.player_step()
        gsm.auto_step()
        game_state_1 = gsm.get_game_state()  # after first skill cast
        p2ac = game_state_1.get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 7)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))
        self.assertTrue(game_state_1.get_player1().get_hand_cards().contains(LightningStiletto))

        # reset opponenet
        game_state_1 = game_state_1.factory().player2(
            self.BASE_GAME.get_player2()
        ).build()

        # second skill by casting skill directly
        gsm = GameStateMachine(game_state_1, a1, a2)
        a1.inject_action(SkillAction(
            skill=CharacterSkill.ELEMENTAL_SKILL1,
            instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
        ))
        gsm.player_step()
        gsm.auto_step()
        game_state_1_1 = gsm.get_game_state()
        p2ac = game_state_1_1.get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 7)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))
        self.assertFalse(game_state_1_1.get_player1().get_hand_cards().contains(LightningStiletto))

        # second skill by using card, when Keqing on field
        source = StaticTarget(Pid.P1, Zone.CHARACTERS, 3)
        gsm = GameStateMachine(game_state_1, a1, a2)
        a1.inject_action(CardAction(
            card=LightningStiletto,
            instruction=StaticTargetInstruction(
                dices=ActualDices({Element.OMNI: 3}),
                target=source,
            )
        ))
        gsm.player_step()
        gsm.auto_step()
        game_state_1_2 = gsm.get_game_state()
        p2ac = game_state_1_2.get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 7)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))
        self.assertFalse(game_state_1_2.get_player1().get_hand_cards().contains(LightningStiletto))

        # second skill by using card, when Keqing off field
        game_state = game_state_1.factory().f_player1(
            lambda p: p.factory().f_characters(
                lambda cs: cs.factory().active_character_id(1).build()
            ).build()
        ).build()
        gsm = GameStateMachine(game_state, a1, a2)
        a1.inject_action(CardAction(
            card=LightningStiletto,
            instruction=StaticTargetInstruction(
                dices=ActualDices({Element.OMNI: 3}),
                target=source,
            )
        ))
        gsm.player_step()
        gsm.auto_step()
        game_state_1_2 = gsm.get_game_state()
        p2ac = game_state_1_2.get_player2().just_get_active_character()
        p1ac = game_state_1_2.get_player1().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 7)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))
        self.assertFalse(game_state_1_2.get_player1().get_hand_cards().contains(LightningStiletto))
        self.assertEqual(type(p1ac), Keqing)

        # reset p2
        game_state_1_2 = game_state_1_2.factory().player2(
            self.BASE_GAME.get_player2()
        ).build()

        # test normal attack electro infused
        gsm = GameStateMachine(game_state_1_2, a1, a2)
        a1.inject_action(SkillAction(
            skill=CharacterSkill.NORMAL_ATTACK,
            instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
        ))
        gsm.player_step()
        gsm.auto_step()
        game_state_infused = gsm.get_game_state()
        p2ac = game_state_infused.get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 8)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))
        self.assertFalse(
            game_state_infused.get_player1().get_hand_cards().contains(LightningStiletto)
        )

        # tests infusion doesn't apply to other characters
        game_state = set_active_player_id(game_state_1_2, Pid.P1, 2)
        gsm = GameStateMachine(game_state, a1, a2)
        a1.inject_action(SkillAction(
            skill=CharacterSkill.NORMAL_ATTACK,
            instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
        ))
        gsm.player_step()
        gsm.auto_step()
        game_state = gsm.get_game_state()
        p2ac = game_state.get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 8)
        self.assertFalse(p2ac.get_elemental_aura().has_aura())
        self.assertFalse(
            game_state.get_player1().get_hand_cards().contains(LightningStiletto)
        )

        # test ElectroInfusion disappear when two round ends
        gsm = GameStateMachine(game_state_infused, LazyAgent(), LazyAgent())
        # initially
        p1ac = gsm.get_game_state().get_player1().just_get_active_character()
        self.assertEqual(
            p1ac.get_character_statuses().just_find(KeqingElectroInfusionStatus).usages,
            2
        )
        # next round
        gsm.step_until_phase(game_state.get_mode().end_phase())
        gsm.step_until_phase(game_state.get_mode().action_phase())
        p1ac = gsm.get_game_state().get_player1().just_get_active_character()
        self.assertEqual(
            p1ac.get_character_statuses().just_find(KeqingElectroInfusionStatus).usages,
            1
        )
        # next round
        gsm.step_until_phase(game_state.get_mode().roll_phase())
        gsm.step_until_phase(game_state.get_mode().action_phase())
        p1ac = gsm.get_game_state().get_player1().just_get_active_character()
        self.assertFalse(p1ac.get_character_statuses().contains(KeqingElectroInfusionStatus))

    def test_elemental_burst(self):
        a1, a2 = PuppetAgent(), PuppetAgent()
        base_game_state = self.BASE_GAME.factory().f_player1(
            lambda p: p.factory().f_characters(
                lambda cs: cs.factory().f_active_character(
                    lambda ac: ac.factory().energy(
                        ac.get_max_energy()
                    ).build()
                ).build()
            ).build()
        ).build()
        pyro_game_state = oppo_aura_elem(base_game_state, Element.PYRO)
        hydro_game_state = oppo_aura_elem(base_game_state, Element.HYDRO)

        # no reaction
        gsm = GameStateMachine(base_game_state, a1, a2)
        a1.inject_action(
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_BURST,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 4})),
            )
        )
        gsm.player_step()
        gsm.auto_step()
        p2cs = gsm.get_game_state().get_player2().get_characters()
        p2c1, p2c2, p2c3 = (p2cs.just_get_character(i) for i in range(1, 4))
        self.assertEqual(p2c1.get_hp(), 6)
        self.assertEqual(p2c2.get_hp(), 7)
        self.assertEqual(p2c3.get_hp(), 7)
        self.assertTrue(p2c1.get_elemental_aura().contains(Element.ELECTRO))
        self.assertFalse(p2c2.get_elemental_aura().elem_auras())
        self.assertFalse(p2c3.get_elemental_aura().elem_auras())
        self.assertEqual(
            gsm.get_game_state().get_player1().just_get_active_character().get_energy(),
            0
        )

        # overloaded
        gsm = GameStateMachine(pyro_game_state, a1, a2)
        a1.inject_action(
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_BURST,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 4})),
            )
        )
        gsm.player_step()
        gsm.auto_step()
        p2cs = gsm.get_game_state().get_player2().get_characters()
        p2c1, p2c2, p2c3 = (p2cs.just_get_character(i) for i in range(1, 4))
        self.assertEqual(p2c1.get_hp(), 4)
        self.assertEqual(p2c2.get_hp(), 7)
        self.assertEqual(p2c3.get_hp(), 7)
        self.assertFalse(p2c1.get_elemental_aura().elem_auras())
        self.assertFalse(p2c2.get_elemental_aura().elem_auras())
        self.assertFalse(p2c3.get_elemental_aura().elem_auras())
        self.assertEqual(
            p2cs.get_active_character_id(),
            2,
        )
        self.assertEqual(
            gsm.get_game_state().get_player1().just_get_active_character().get_energy(),
            0,
        )

        # electro-charged
        gsm = GameStateMachine(hydro_game_state, a1, a2)
        a1.inject_action(
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_BURST,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 4})),
            )
        )
        gsm.player_step()
        gsm.auto_step()
        p2cs = gsm.get_game_state().get_player2().get_characters()
        p2c1, p2c2, p2c3 = (p2cs.just_get_character(i) for i in range(1, 4))
        self.assertEqual(p2c1.get_hp(), 5)
        self.assertEqual(p2c2.get_hp(), 6)
        self.assertEqual(p2c3.get_hp(), 6)
        self.assertFalse(p2c1.get_elemental_aura().elem_auras())
        self.assertFalse(p2c2.get_elemental_aura().elem_auras())
        self.assertFalse(p2c3.get_elemental_aura().elem_auras())
        self.assertEqual(
            gsm.get_game_state().get_player1().just_get_active_character().get_energy(),
            0,
        )

    def test_talent_card(self):
        a1, a2 = PuppetAgent(), PuppetAgent()
        source = StaticTarget(Pid.P1, Zone.CHARACTERS, 3)
        # test early equip
        gsm = GameStateMachine(self.BASE_GAME, a1, a2)
        a1.inject_actions([
            CardAction(
                card=ThunderingPenance,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
            ),
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_SKILL1,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
            ),
            SkillAction(
                skill=CharacterSkill.NORMAL_ATTACK,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
            )
        ])
        gsm.player_step()
        gsm.auto_step()
        gsm.player_step()
        gsm.auto_step()
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 4)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))

        gsm.player_step()
        gsm.auto_step()
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 1)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))

        # test late equip
        gsm = GameStateMachine(self.BASE_GAME, a1, a2)
        a1.inject_actions([
            SkillAction(
                skill=CharacterSkill.ELEMENTAL_SKILL1,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
            ),
            CardAction(
                card=ThunderingPenance,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
            ),
            SkillAction(
                skill=CharacterSkill.NORMAL_ATTACK,
                instruction=DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
            )
        ])
        gsm.player_step()
        gsm.auto_step()
        gsm.player_step()
        gsm.auto_step()
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 4)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))

        gsm.player_step()
        gsm.auto_step()
        p2ac = gsm.get_game_state().get_player2().just_get_active_character()
        self.assertEqual(p2ac.get_hp(), 1)
        self.assertTrue(p2ac.get_elemental_aura().contains(Element.ELECTRO))

    def test_lightning_stiletto_usability(self):
        game_state = self.BASE_GAME.factory().f_player1(
            lambda p: p.factory().f_characters(
                lambda cs: cs.factory().f_active_character(
                    lambda ac: ac.factory().f_character_statuses(
                        lambda sts: sts.update_status(FrozenStatus())
                    ).build()
                ).build()
            ).f_hand_cards(
                lambda hcs: hcs.add(LightningStiletto)
            ).build()
        ).build()

        self.assertFalse(LightningStiletto.loosely_usable(game_state, Pid.P1))
        self.assertIsNone(LightningStiletto.valid_instruction(
            game_state,
            Pid.P1,
            DiceOnlyInstruction(dices=ActualDices({Element.OMNI: 3})),
        ))
        # False because frozen
        self.assertIsNone(LightningStiletto.valid_instruction(
            game_state,
            Pid.P1,
            StaticTargetInstruction(
                dices=ActualDices({Element.OMNI: 3}),
                target=StaticTarget(
                    pid=Pid.P1,
                    zone=Zone.CHARACTERS,
                    id=3,
                )
            ),
        ))
