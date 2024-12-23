import unittest
from and_tree import ANDTreeSearch, ANDTreeNode
from models import Game, Practice, GameSlot, PracticeSlot, Preference, make_game_or_practice_obj, PairConstraint, Incompatible, Unwanted, PartialAssignments
from soft_constraints import soft_penalty, partial_soft_penalty, min_filled, prefrences, paired, sec_diff
from hard_constraints import satisfies_hard_constraints, game_capacity,practice_capacity,overlapping_games_practices,late_divisions, no_tuesday_eleven ,overlapping_tiers,cmsa_tuesday,incompatibilities, unwanted, cmsa_overlapping_tiers

class TestANDTreeSearch(unittest.TestCase):
    def setUp(self):
        """
        Set up test data for all test cases.
        """
        self.games = [
            Game("Game 1", "CMSA", "U13T3", "01"),
            Game("Game 2", "CMSA", "U13T3", "02"),
            Game("Game 3", "CUSA", "O18", "01"),
            Game("Game 4", "CMSA", "U17T1", "01"),
            Game("Game 5", "CMSA" ,"U17T1", "09"),
            Game("Game 6", "CMSA", "U15T1S", "01"),
            Game("Game 7", "CMSA", "U12T1", "01"),
        ]

        self.practices = [
            Practice("Practice 1", "CMSA", "U13T1", "01", "PRC 01"),
            Practice("Practice 2", "CMSA", "U13T1S", "01", "PRC 01"),
            Practice("Practice 3", "CMSA", "U13T3", "02", "OPN 02"),
            Practice("Practice 4", "CUSA", "O18", "01", "PRC 01"),
            Practice("Practice 5", "CMSA", "U17T1", "01", "PRC 01"),
            Practice("Practice 6", "CMSA", "U12T1S", "01", "PRC 01"),

        ]

        self.game_slots = [
            GameSlot("Slot A", "MO", "8:00", 3, 1),
            GameSlot("Slot B", "MO", "9:00", 3, 1),
            GameSlot("Slot C", "TU", "9:30", 2, 1),
            GameSlot("Slot D", "TU", "18:00", 2, 1),
            GameSlot("Slot E", "TU", "11:00", 2, 1),
        ]

        self.practice_slots = [
            PracticeSlot("Slot G", "MO", "8:00", 4, 1),
            PracticeSlot("Slot H", "TU", "10:00", 2, 1),
            PracticeSlot("Slot I", "FR", "10:00", 2, 1),
            PracticeSlot("Slot J", "TU", "18:00", 2, 1),
        ]

        self.incompatibilities = [
            Incompatible(identifier="inc1",
                         game_or_practice1=Practice("Practice 1", "CMSA", "U13T1", "01", "PRC 01"),
                         game_or_practice2=Practice("Practice 3", "CMSA", "U13T3", "02", "OPN 02")),
            Incompatible("inc2",
                         Game("Game 4", "CMSA", "U17T1", "01"),
                         Game("Game 1", "CMSA", "U13T3", "01")),

            Incompatible("inc3",
                         Game("Game 4", "CMSA", "U17T1", "01"),
                         Game("Game 2", "CMSA", "U13T3", "02")),

            Incompatible("inc4",
                         Practice("Practice 5", "CMSA", "U17T1", "00", "PRC 01"),
                         Game("Game 2", "CMSA", "U13T3", "02")),

            Incompatible("inc5",
                         Game("Game 1", "CMSA", "U13T3", "01"),
                         Practice("Practice 5", "CMSA", "U17T1", "00", "PRC 01")),
        ]

        self.unwanted = [
            Unwanted(identifier="Unwanted 1",
                     game_or_practice=Game("Game 1", "CMSA", "U13T3", "01"),
                     slot_day="MO",
                     slot_time="8:00")
        ]

        self.preferences = [
            Preference(identifier=1, slot_day="MO", slot_time="8:00", game_or_practice=make_game_or_practice_obj("Game 1", "CMSA U13T3 DIV 01"),
                       preference_value=1),
            Preference(identifier=2, slot_day="TU", slot_time="10:00", game_or_practice=make_game_or_practice_obj("Practice 2", "CMSA U13T3 DIV 02 OPN 02"),
                       preference_value=1),
            Preference(identifier=3, slot_day="TU", slot_time="9:30", game_or_practice=make_game_or_practice_obj("Game 2", "CMSA U13T3 DIV 02"),
                       preference_value=1),
            Preference(identifier=4, slot_day="TU", slot_time="10:00", game_or_practice=make_game_or_practice_obj("Practice 1", "CMSA U13T3 DIV 01 PRC 01"),
                       preference_value=1),
            Preference(identifier=5, slot_day="MO", slot_time="2:00", game_or_practice=make_game_or_practice_obj("Game 4", "CMSA U17T1 DIV 01"),
                       preference_value=1),
            Preference(identifier=6, slot_day="MO", slot_time="10:00", game_or_practice=make_game_or_practice_obj("Practice 1", "CMSA U13T3 DIV 01 PRC 01"),
                       preference_value=1)
        ]

        self.pairs = [
            PairConstraint(identifier="Pair1",
                           game_or_practice1=Game("Game 3", "CUSA", "O18", "01"),
                           game_or_practice2=Game("Game 4", "CMSA", "U17T1", "01")
                           ),
            PairConstraint(identifier="Pair2",
                           game_or_practice1=Game("Game 3", "CUSA", "O18", "01"),
                           game_or_practice2=Practice("Practice 1", "CMSA", "U13T1", "01", "PRC 01")
                           )
        ]

        self.partial_assignments = [
            PartialAssignments(
                identifier="pa1",
                game_or_practice=Game("Game 3", "CUSA", "O18", "01"),
                slot_day="MO",
                slot_time="8:00"),

            PartialAssignments(
                identifier="pa2",
                game_or_practice=Practice("Practice 4", "CUSA", "O18", "01", "PRC 01"),
                slot_day="FR",
                slot_time="10:00")
        ]

        self.search = ANDTreeSearch(
            self.games,
            self.practices,
            self.game_slots,
            self.practice_slots,
            self.incompatibilities,
            self.preferences,
            self.pairs,
            partial_assignments=[],
            unwanted=self.unwanted,
            weights=[1, 1, 1, 1, 1, 1, 1, 1]
        )



    def test_min_filled(self):
        """
        Test the min filled soft constraint.
        """
        # Case 1: All slots meet or exceed the minimum requirement
        solution = {
            self.game_slots[0]: [self.games[0], self.games[1]],  # Min: 1, Actual: 2
            self.practice_slots[0]: [self.practices[0], self.practices[1]],  # Min: 1, Actual: 2
            self.game_slots[1]: [self.games[2]],  # Min: 1, Actual: 1
            self.practice_slots[1]: [self.practices[2]],  # Min: 1, Actual: 1
            self.game_slots[2]: [self.games[3]],  # Min: 1, Actual: 1
            self.practice_slots[2]: [self.practices[3]],  # Min: 1, Actual: 1
        }

        score = min_filled(solution, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 0, "All slots meet or exceed minimum requirements, score should be 0.")

        # Case 2: Two slots have fewer than the minimum requirement
        solution = {
            self.game_slots[0]: [self.games[0]],  # Min: 1, Actual: 1
            self.practice_slots[0]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.game_slots[1]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.practice_slots[1]: [self.practices[1]],  # Min: 1, Actual: 1
            self.game_slots[2]: [self.games[2]],  # Min: 1, Actual: 1
            self.practice_slots[2]: [self.practices[2]],  # Min: 1, Actual: 1
        }

        expected_penalty = 2  # Two slots have fewer than the minimum
        score = min_filled(solution, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, expected_penalty, f"Two slots have fewer than the minimum, score should be {expected_penalty}.")

        # Case 3: All slots are empty
        solution = {
            self.game_slots[0]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.practice_slots[0]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.game_slots[1]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.practice_slots[1]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.game_slots[2]: [],  # Min: 1, Actual: 0 (Penalty: +1)
            self.practice_slots[2]: [],  # Min: 1, Actual: 0 (Penalty: +1)
        }

        expected_penalty = 6  # All six slots are underfilled
        score = min_filled(solution, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, expected_penalty, f"All slots are empty, score should be {expected_penalty}.")

    
    def test_preferences(self):
        """
        Test scenarios where all, some, or none of the preferences are met.
        """

        # Case 1: All preferences are met
        solution_all_met = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" scheduled in "MO 8:00" (meets preference)
            self.practice_slots[1]: [self.practices[1]],  # "CMSA U13T3 DIV 02 OPN 02" scheduled in "TU 10:00" (meets preference)
        }

        score = prefrences(solution_all_met, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 0, "All preferences met should result in a score of 0.")

        # Case 2: Some preferences are met
        solution_some_met = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" scheduled in "MO 8:00" (meets preference)
            self.practice_slots[1]: [self.practices[1]],  # "CMSA U13T3 DIV 02 OPN 02" scheduled in "TU 10:00" (meets preference)
            self.game_slots[2]: [self.games[3]],  # "CMSA U17T1 DIV 01" scheduled in "TU 9:30" (does not meet preference)
        }

        expected_unmet_preferences = 1  # One preference not met
        score = prefrences(solution_some_met, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, expected_unmet_preferences, f"Some preferences not met should result in a score of {expected_unmet_preferences}.")

        # Case 3: No preferences are met
        solution_none_met = {
            self.game_slots[1]: [self.games[3]],  # "CMSA U17T1 DIV 01" scheduled in "TU 9:30" (does not meet preference)
            self.practice_slots[2]: [self.practices[2]],  # "CMSA U17T1 PRC 01" scheduled in "FR 10:00" (does not meet preference)
        }

        score = prefrences(solution_none_met, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 2, f"No preferences met should result in a score of {2}.")


    def test_game_capacity(self):
        """
        Test the game capacity hard constraint.
        """
        # Case 1: All slots are within capacity
        solution = {
            self.game_slots[0]: [self.games[0], self.games[1]],  # 2 games
            self.game_slots[1]: [self.games[2]],  # 1 game
            self.game_slots[2]: [self.games[3]],  # 1 game
        }

        self.assertTrue(game_capacity(solution, self.incompatibilities, self.unwanted), "All slots are within capacity, should return True.")

        # Case 2: One slot exceeds capacity
        solution = {

            self.game_slots[2]: [ self.games[0], self.games[1], self.games[2]],  # 4 games
        }

        self.assertFalse(game_capacity(solution, self.incompatibilities, self.unwanted), "One slot exceeds capacity, should return False.")


    def test_overlap_games_practices(self):
        """
        Test the overlapping games and practices hard constraint.
        """
        # Case 1: No overlapping slots
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" in "MO 8:00"
            self.practice_slots[1]: [self.practices[1]],  # "CMSA U13T3 DIV 02 OPN 02" in "TU 10:00"
        }

        self.assertTrue(overlapping_games_practices(solution, self.incompatibilities, self.unwanted), "No overlapping slots, should return True.")

        # Case 2: Overlapping game and practice
        solution = {
            self.game_slots[0]: [self.games[0]],  # Game 1 assigned to Slot A
            self.practice_slots[0]: [self.practices[0]],  # Practice 1 assigned to Slot D
        }

        # Ensure matching league, tier, and division
        self.games[0].league = "CMSA"
        self.games[0].tier = "U13T3"
        self.games[0].division = 1

        self.practices[0].league = "CMSA"
        self.practices[0].tier = "U13T3"
        self.practices[0].division = 1

        # Set overlapping time for Slot A and Slot D
        self.game_slots[0].end_time = 9.0
        self.practice_slots[0].start_time = 8.5
        self.practice_slots[0].end_time = 9.5

        # Debug logs
        # print(f"[DEBUG] Game Slot A: {self.game_slots[0].start_time}-{self.game_slots[0].end_time}, Day: {self.game_slots[0].day}")
        # print(f"[DEBUG] Practice Slot D: {self.practice_slots[0].start_time}-{self.practice_slots[0].end_time}, Day: {self.practice_slots[0].day}")

        self.assertFalse(overlapping_games_practices(solution, self.incompatibilities, self.unwanted), "Overlapping slots, should return False.")

    def test_incompat(self):
        """
        Test the incompatibilities hard constraint with preserved format.
        """
        # print(f"[DEBUG] Incompatibilities list: {self.incompatibilities}")

        # Case 1: No incompatibilities
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01"
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02"
        }
        # print("[DEBUG] Testing Case 1: No incompatibilities")
        self.assertTrue(
            incompatibilities(solution, self.incompatibilities, self.unwanted),
            "No incompatibilities, should return True."
        )

        # Case 2: Incompatibility found
        solution = {
            self.game_slots[0]: [self.games[0], self.games[3]],
        }
        # print("[DEBUG] Testing Case 2: Incompatibility found")
        self.assertFalse(
            incompatibilities(solution, self.incompatibilities, self.unwanted),
            "Incompatibility found, should return False."
        )
        # Case 3: Incompatibility found practice to game
        solution = {
            self.game_slots[0]: [self.games[1]],
            self.practice_slots[0]: [self.practices[4]]# Both "CMSA U13T3 DIV 01" and "CMSA U17T1 PRC 01" MO 8:00 am
        }
        # print("[DEBUG] Testing Case 2: Incompatibility found")
        self.assertFalse(
            incompatibilities(solution, self.incompatibilities, self.unwanted),
            "Incompatibility found, should return False."
        )

    def test_unwanted(self):
        """
        Test the unwanted hard constraint.
        """
        # Case 1: No unwanted assignments
        
        solution = {
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02" in "MO 9:00"
        }
        self.assertTrue(unwanted(solution, self.incompatibilities, self.unwanted), "No unwanted assignments, should return True.")

        # Case 2: late division not playing late
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" in "MO 8:00" (unwanted)
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02" in "MO 9:00"
            self.game_slots[2]: [self.games[4]],  # "CMSA U17T1 DIV 09" in "TU 9:30"
        }
        self.assertFalse(unwanted(solution, self.incompatibilities, self.unwanted), "Unwanted assignment found, should return False.")

    def test_late_divisions(self):
        """
        Test the late divisions hard constraint.
        """
        # Case 1: late division plays late
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" in "MO 8:00"
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02" in "MO 9:00"
            self.game_slots[3]: [self.games[4]],  # "CMSA U17T1 DIV 09" in "TU 18:00"
        }

        self.assertTrue(late_divisions(solution, self.incompatibilities, self.unwanted), "No late divisions, should return True.")

        # Case 2: Late division found
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" in "MO 8:00"
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02" in "MO 9:00"
            self.game_slots[2]: [self.games[4]],  # "CMSA U17T1 DIV 09" in "TU 9:30" (late division)
        }

        self.assertFalse(late_divisions(solution, self.incompatibilities, self.unwanted), "Late division found, should return False.")

    def test_no_tuesday_eleven(self):
        """
        Test the no Tuesday 12-1 hard constraint.
        """
        # Case 1: No Game Tuesday 11-1230 slot
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" in "MO 8:00"
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02" in "MO 9:00"
            self.game_slots[2]: [self.games[4]],  # "CMSA U17T1 DIV 09" in "TU 9:30"
        }

        self.assertTrue(no_tuesday_eleven(solution, self.incompatibilities, self.unwanted), "No Tuesday 12-1 slot, should return True.")

        # Case 2: Tuesday 11-1230 slot found
        solution = {
            self.game_slots[0]: [self.games[0]],  # "CMSA U13T3 DIV 01" in "MO 8:00"
            self.game_slots[1]: [self.games[1]],  # "CMSA U13T3 DIV 02" in "MO 9:00"
            self.game_slots[4]: [self.games[3]],  # "CMSA U17T1 DIV 09" in "TU 11:00" 
        }

        self.assertFalse(no_tuesday_eleven(solution, self.incompatibilities, self.unwanted), "Tuesday 11-1230 slot found, should return False.")


    def test_pairs(self):
        # case 1: paired together, no penalty
        solution = {
            self.game_slots[0]: [self.games[2], self.games[3]], # CUSA 018 DIV 01 and CMSA U17T1 DIV 01 together
            self.practice_slots[0]: [self.practices[0]]
        }
        score = paired(solution, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 0, f"Paired games are together, penalty expected: 0, given: {score}.")

        # case 2: not paired together, penalty 1
        solution = {
            self.game_slots[0]: [self.games[2]],
            self.game_slots[1]: [self.games[3]],                   # CUSA 018 DIV 01 and CMSA U17T1 DIV 01 together
            self.practice_slots[0]: [self.practices[0]]
        }
        score = paired(solution, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 1, f"Paired games not together, penalty expected: 1, given: {score}.")

        # case 3: not paired together, penalty 2
        solution = {
            self.game_slots[0]: [self.games[3]],
            self.game_slots[1]: [self.games[2]],                   # CUSA 018 DIV 01 and CMSA U17T1 DIV 01 together
            self.practice_slots[0]: [self.practices[0]]
        }
        score = paired(solution, self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 2, f"Paired games not together, penalty expected: 2, given: {score}.")


    def test_overlapping_tiers(self):
        #case 1 no overlap in tiers
        solution = {
            self.game_slots[0]: [self.games[4]],
            self.game_slots[1]: [self.games[5]]
        }

        self.assertTrue(overlapping_tiers(solution, self.incompatibilities, self.unwanted), "No overlapping tiers, should return True.")

        #case 2 overlap
        solution = {
            self.game_slots[0]: [self.games[4], self.games[5]]
        }

        self.assertFalse(overlapping_tiers(solution, self.incompatibilities, self.unwanted),
                        "Overlapping, should return False.")

    def test_csma_special_overlap(self):
        #case 1 no overlap
        solution = {
            self.game_slots[0]: [self.games[6]],
            self.practice_slots[1]: [self.practices[5]]
        }

        self.assertTrue(cmsa_overlapping_tiers(solution, self.incompatibilities, self.unwanted))

        #case 2 overlap
        solution = {
            self.game_slots[0]: [self.games[6]],
            self.practice_slots[0]: [self.practices[5]]
        }

        self.assertFalse(cmsa_overlapping_tiers(solution, self.incompatibilities, self.unwanted))



    def test_cmsa_tuesday(self):
        # Case 1 CMSA U13T1 is tu 18:00-19:00
        solution = {
            self.practice_slots[3]: [self.practices[0]],  # "CMSA U13T1 DIV 01" in "TU 18:00"
        }

        self.assertTrue(cmsa_tuesday(solution, self.incompatibilities, self.unwanted), "CMSA U13T1 is tu 18:00-19:00, should return True.")

        # Case 2: CMSA U13T1 is not tu 18:00-19:00
        solution = {
            self.practice_slots[2]: [self.practices[1]],  # "CMSA U13T1S DIV 01" in "TU 18:00"
        }

        self.assertFalse(cmsa_tuesday(solution, self.incompatibilities, self.unwanted), "CMSA U13T1 is not tu 18:00-19:00, should return False.")
        


if __name__ == "__main__":

    unittest.main()