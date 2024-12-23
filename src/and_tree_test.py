import unittest
from and_tree import ANDTreeSearch, ANDTreeNode
from models import Game, Incompatible, PairConstraint, PartialAssignments, Practice, GameSlot, PracticeSlot, Preference, Unwanted, make_game_or_practice_obj
from soft_constraints import soft_penalty, partial_soft_penalty
from hard_constraints import satisfies_hard_constraints

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
        ]

        self.practices = [
            Practice("Practice 1", "CMSA", "U13T1", "01", "PRC 01"),
            Practice("Practice 2", "CMSA", "U13T1S", "01", "PRC 01"),
            Practice("Practice 3", "CMSA", "U13T3", "02", "OPN 02"),
            Practice("Practice 4", "CUSA", "O18", "01", "PRC 01"),
            Practice("Practice 5", "CMSA", "U17T1", "01", "PRC 01"),
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
        
    def test_initialization(self):
        """
        Test initialization of ANDTreeSearch.
        """
        self.assertEqual(self.search.games, self.games)
        self.assertEqual(self.search.practices, self.practices)
        self.assertEqual(self.search.game_slots, self.game_slots)
        self.assertEqual(self.search.practice_slots, self.practice_slots)
        self.assertEqual(self.search.incompatibilities, self.incompatibilities)
        self.assertIsInstance(self.search.root, ANDTreeNode)
        self.assertIsNotNone(self.search.root.solution)

    def test_hard_constraints(self):
        """
        Test hard constraints.
        """
        partial_solution = {
            self.game_slots[0]: [self.games[0]],
            self.practice_slots[0]: [self.practices[0]],
        }
        self.assertTrue(satisfies_hard_constraints(partial_solution, self.incompatibilities, self.unwanted))

        partial_solution[self.game_slots[0]].extend([self.games[1], self.games[2]])
        self.assertFalse(satisfies_hard_constraints(partial_solution, self.incompatibilities, self.unwanted))

        partial_solution = {
            self.game_slots[0]: [self.games[0]],
        }
        self.assertFalse(satisfies_hard_constraints(partial_solution, self.incompatibilities, self.unwanted))

        partial_solution = {
            self.practice_slots[0]: [self.practices[2]],
        }
        self.assertFalse(satisfies_hard_constraints(partial_solution, self.incompatibilities, self.unwanted))

    def test_soft_constraints(self):
        """
        Test soft constraints evaluation.
        """
        solution = {
            self.game_slots[0]: [self.games[0]],
            self.game_slots[1]: [self.games[1]],
            self.practice_slots[0]: [self.practices[0]],
        }

        score = soft_penalty(solution,  self.search.weights, self.preferences, self.pairs)
        self.assertEqual(score, 0)  # todo calculate actual score

    def test_search(self):
        """
        Test the AND-tree search process.
        """
        best_solution, best_score = self.search.run_search()

        self.assertIsNotNone(best_solution)
        self.assertIsInstance(best_score, (int, float))
        self.assertTrue(satisfies_hard_constraints(best_solution, self.incompatibilities, self.unwanted))

    def test_no_solution(self):
        """
        Test when no solution is possible.
        """
        self.search.incompatibilities = [
            ("Game 1", "Game 2"), 
            ("Game 2", "Game 1"),
            ("Game 3", "Practice 1"), 
            ("Game 3", "Practice 2"), 
            ("Game 3", "Practice 3")
        ]

        for slot in self.game_slots + self.practice_slots:
            slot.gamemax = 0
            slot.practicemax = 0

        best_solution, best_score = self.search.run_search()

        self.assertIsNone(best_solution)
        self.assertEqual(best_score, float('inf'))

    def test_edge_case_slots(self):
        """
        Test edge cases with unusual slots.
        """
        self.game_slots.append(GameSlot("Edge Slot", "Friday", "23:00", 1, 0))
        partial_solution = {self.game_slots[-1]: [self.games[0]]}
        self.assertTrue(satisfies_hard_constraints(partial_solution, self.incompatibilities, self.unwanted))

        partial_solution[self.game_slots[-1]].append(self.games[1])
        self.assertFalse(satisfies_hard_constraints(partial_solution, self.incompatibilities, self.unwanted))

    def test_random_tie_breaking(self):
        """
        Test randomness in tie-breaking during search.
        """
        import random
        random.seed(42)
        self.search.depth_first_search(self.search.root)
        first_solution = self.search.best_solution

        random.seed(42)
        self.search.depth_first_search(self.search.root)
        second_solution = self.search.best_solution

        self.assertEqual(first_solution, second_solution)
        
    def test_expand_node(self):
        """
        Test the expand_node function for prioritizing the most constrained game and assigning practices.
        """
        # Create a partial solution with all slots
        partial_solution = {
            slot: [] for slot in self.game_slots + self.practice_slots
        }
        partial_solution[self.game_slots[0]].append(self.games[0])  # Assign Game 1 to Slot A

        node = ANDTreeNode(solution=partial_solution)

        # Expand the node
        self.search.expand_node(node)

        # Check if expansions were created
        unassigned_games = [
            g for g in self.games if not any(g in assignments for assignments in node.solution.values())
        ]
        self.assertGreater(len(unassigned_games), 0, "All games are already assigned.")

        # Check if the most constrained game has valid expansions
        most_constrained_game = min(
            unassigned_games,
            key=lambda g: len([
                slot for slot in self.game_slots
                if (matching_slot := self.search.get_matching_slot(slot, partial_solution)) and satisfies_hard_constraints(
                    self.search.get_hypothetical_solution(g, matching_slot, partial_solution),
                    self.incompatibilities,
                    self.unwanted
                )
            ])
        )

        # print(f"[DEBUG] Most constrained game: {most_constrained_game.id}")

        expanded_slots = [
            child.solution for child in node.unexplored_children
            if most_constrained_game in [item for slot in child.solution.values() for item in slot]
        ]
        self.assertGreater(len(expanded_slots), 0, "No expansions were created for the most constrained game.")

        # Verify that expanded nodes satisfy hard constraints
        for child in node.unexplored_children:
            self.assertTrue(
                satisfies_hard_constraints(child.solution, self.incompatibilities, self.unwanted),
                "Expanded node violates hard constraints."
            )
if __name__ == "__main__":
    unittest.main()