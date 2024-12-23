import os
import time
import threading
import logging
import logging.handlers
from queue import Queue
import cProfile

from models import Game, GameSlot, Practice, PracticeSlot
from input_parser import read_input
from hard_constraints import satisfies_hard_constraints
from soft_constraints import soft_penalty, partial_soft_penalty

def time_to_float(time_str):
    # Convert a "HH:MM" time string into a float representing hours.
    # Useful for comparing and sorting times numerically.
    hours, minutes = map(int, time_str.split(":"))
    return hours + minutes / 60

# Global state dictionary to track progress and best score during search
progress_state = {
    "expanded_nodes": 0,
    "best_score": float('inf'),
    "start_time": time.time(),
    "done": False,
    "assigned_games": 0,
    "assigned_practices": 0
}

def progress_monitor(interval=1.0):
    # Periodically print out the current search progress.
    # Helpful for long-running searches to see how many nodes have expanded,
    # what the best found score is, and how much time has elapsed.
    while True:
        time.sleep(interval)
        expanded = progress_state["expanded_nodes"]
        best_score = progress_state["best_score"]
        assigned_games = progress_state["assigned_games"]
        assigned_practices = progress_state["assigned_practices"]
        done = progress_state["done"]
        elapsed = time.time() - progress_state["start_time"]
        print(f"[Progress Monitor] Expanded: {expanded} nodes, "
              f"Best Score: {best_score}, "
              f"Assigned Games: {assigned_games}, "
              f"Assigned Practices: {assigned_practices}, "
              f"Elapsed: {elapsed:.2f}s")
        if done:
            break

class ANDTreeNode:
    # Basic node structure for our AND/OR tree search.
    # Contains the current partial/complete solution and references to child nodes.
    def __init__(self, solution, parent=None):
        self.solution = solution
        self.parent = parent
        self.explored_children = []
        self.unexplored_children = []
        self.is_pruned = False

    def add_child(self, child):
        # Add a child node to the current node's unexplored children list.
        self.unexplored_children.append(child)

class ANDTreeSearch:
    # Main class implementing the AND-tree search for scheduling.
    # Handles reading inputs, setting up constraints, performing search,
    # and pruning suboptimal or invalid solutions.
    def __init__(self, games, practices, game_slots, practice_slots, incompatibilities, preferences, pairs, partial_assignments, weights, unwanted, logger):
        # Store all problem data and search parameters
        self.games = games
        self.practices = practices
        self.game_slots = game_slots
        self.practice_slots = practice_slots
        self.incompatibilities = incompatibilities
        self.preferences = preferences
        self.pairs = pairs
        self.partial_assignments = partial_assignments
        self.unwanted = unwanted
        self.weights = weights
        self.logger = logger

        # Build a quick-access map for incompatibilities
        self.incompat_map = {}
        for inc in incompatibilities:
            i1, i2 = inc.game_or_practice1, inc.game_or_practice2
            self.incompat_map.setdefault(i1, set()).add(i2)
            self.incompat_map.setdefault(i2, set()).add(i1)

        self.hard_constraint_cache = {}
        
        # Initialize the root node with any partial assignments applied
        self.root = ANDTreeNode(solution=self.initialize_solution_with_partial_assignments())
        
        # We don't know the best solution yet
        self.best_solution = None

        self.logger.debug("Initialization complete. Starting solution:\n %s", self.root.solution)

    def initialize_solution_with_partial_assignments(self):
        # Integrate given partial assignments into the initial solution.
        # If any partial assignment violates constraints, remove it.
        solution = {slot: [] for slot in self.game_slots + self.practice_slots}
        for assignment in self.partial_assignments:
            item = assignment.game_or_practice
            slot = next((s for s in solution if s.day == assignment.slot_day and abs(s.start_time - assignment.slot_time) < 1e-9), None)
            if not slot:
                raise ValueError(f"Invalid partial assignment: {assignment}")
            solution[slot].append(item)
            # Check constraints immediately after adding
            if not satisfies_hard_constraints(solution, self.incompatibilities, self.unwanted, self.incompat_map):
                self.logger.debug("Partial assignment %s violates constraints. Removing.", item.id)
                solution[slot].remove(item)
        return solution

    def canonical_solution_representation(self, solution):
        # Represent the solution state as a sorted tuple of (slot_id, item_id) pairs.
        # Useful for detecting already visited states and caching.
        items_list = []
        for slot, assigns in solution.items():
            for it in assigns:
                items_list.append((slot.id, it.id))
        items_list.sort()
        return tuple(items_list)

    def check_hard_constraints(self, solution):
        # Check if current solution state satisfies all hard constraints.
        # Use a cache to avoid recomputing for the same state.
        rep = self.canonical_solution_representation(solution)
        if rep in self.hard_constraint_cache:
            return self.hard_constraint_cache[rep]
        result = satisfies_hard_constraints(solution, self.incompatibilities, self.unwanted, self.incompat_map)
        self.hard_constraint_cache[rep] = result
        if not result:
            self.logger.debug("Hard constraints failed for solution state.")
        return result

    def get_matching_slot(self, slot, solution):
        # Find the slot in the solution dictionary that matches the given slot by ID, day, and time.
        return next((s for s in solution if s.id == slot.id and s.day == slot.day and abs(s.start_time - slot.start_time) < 1e-9), None)

    def get_hypothetical_solution(self, item, slot, solution):
        # Given an item and a slot, try to produce a new solution state with this item assigned to that slot.
        new_solution = {key: list(value) for key, value in solution.items()}
        matching_slot = self.get_matching_slot(slot, new_solution)
        if not matching_slot:
            return None
        new_solution[matching_slot].append(item)
        return new_solution

    def is_solution_complete(self, solution):
        # Check if all games and all practices are assigned.
        all_games_assigned = all(any(g in assigns for assigns in solution.values()) for g in self.games)
        all_practices_assigned = all(any(p in assigns for assigns in solution.values()) for p in self.practices)
        return all_games_assigned and all_practices_assigned

    def count_assigned_games(self, solution):
        # Count how many unique games are assigned in the current solution.
        assigned_games = {it for assigns in solution.values() for it in assigns if isinstance(it, Game)}
        return len(assigned_games)

    def count_assigned_practices(self, solution):
        # Count how many unique practices are assigned in the current solution.
        assigned_practices = {it for assigns in solution.values() for it in assigns if isinstance(it, Practice)}
        return len(assigned_practices)

    def find_feasible_slots(self, item, solution, slots):
        # For a given item and candidate slots, find all feasible slots that don't violate hard constraints.
        # Also compute partial penalty for each hypothetical assignment.
        feasible = []
        for slot in slots:
            hypo = self.get_hypothetical_solution(item, slot, solution)
            if hypo and self.check_hard_constraints(hypo):
                pscore = partial_soft_penalty(hypo, self.weights, self.preferences, self.pairs)
                feasible.append((slot, pscore, hypo))
        return feasible

    def place_item_with_lowest_penalty(self, item, solution, candidate_slots):
        # Assign the given item to the slot that yields the lowest partial penalty increase.
        feasible = self.find_feasible_slots(item, solution, candidate_slots)
        if not feasible:
            return None
        feasible.sort(key=lambda x: x[1])  # sort by partial penalty
        best_hypo = feasible[0][2]
        return best_hypo

    def place_unassociated_practices_first(self, solution):
        # Before assigning games, try to place all unassociated practices to avoid late issues.
        current_solution = {k: list(v) for k,v in solution.items()}
        assigned_practices = {it for assigns in current_solution.values() for it in assigns if isinstance(it, Practice)}
        unassigned = [p for p in self.practices if p not in assigned_practices]

        def is_associated(p):
            # A practice is associated if it matches league/tier/division of some game
            return any((p.league == g.league and p.tier == g.tier and p.division == g.division) for g in self.games)
        unassociated_practices = [p for p in unassigned if not is_associated(p)]

        for p in unassociated_practices:
            placed = False
            for ps in self.practice_slots:
                hypo = self.get_hypothetical_solution(p, ps, current_solution)
                if hypo and self.check_hard_constraints(hypo):
                    # Compute partial penalty to see if continuing is promising
                    pscore = partial_soft_penalty(hypo, self.weights, self.preferences, self.pairs)
                    if pscore >= progress_state["best_score"]:
                        # This partial assignment cannot surpass current best
                        # Prune and return None
                        return None
                    # If promising, update current_solution
                    current_solution = hypo
                    placed = True
                    break
            if not placed:
                # Couldn't place this unassociated practice anywhere
                return None
            current_solution = hypo
        return current_solution

    def assign_associated_practices_greedily(self, game, solution):
        # Once we pick a game slot, we greedily assign associated practices that match the game’s league/tier/div.
        associated_practices = [
            p for p in self.practices
            if p.league == game.league 
            and p.tier == game.tier 
            and p.division == game.division
        ]
        current_solution = {k: list(v) for k, v in solution.items()}

        for practice in associated_practices:
            if any(practice in assigns for assigns in current_solution.values()):
                continue  # Already assigned this practice
            assigned = False
            for ps in self.practice_slots:
                hypo = self.get_hypothetical_solution(practice, ps, current_solution)
                if hypo and self.check_hard_constraints(hypo):
                    # Compute partial penalty after this placement
                    pscore = partial_soft_penalty(hypo, self.weights, self.preferences, self.pairs)
                    if pscore >= progress_state["best_score"]:
                        # No chance to improve, prune
                        return None
                    current_solution = hypo
                    assigned = True
                    break
            if not assigned:
                # Couldn't place associated practice
                return None
            current_solution = hypo
        return current_solution

    def place_one_most_constrained_unassociated(self, solution):
        # Try to place just one most constrained unassociated practice to guide the search initially.
        current_solution = {k: list(v) for k,v in solution.items()}
        assigned_practices = {it for assigns in current_solution.values() for it in assigns if isinstance(it, Practice)}
        unassigned = [p for p in self.practices if p not in assigned_practices]

        def is_associated(p):
            return any((p.league == g.league and p.tier == g.tier and p.division == g.division) for g in self.games)
        unassociated_practices = [p for p in unassigned if not is_associated(p)]

        if not unassociated_practices:
            # No unassociated practice left, nothing to do
            return current_solution

        # Find the unassociated practice with the fewest feasible slots
        practice_feasibility = []
        for p in unassociated_practices:
            feasible = self.find_feasible_slots(p, current_solution, self.practice_slots)
            if feasible:
                practice_feasibility.append((p, len(feasible)))

        if not practice_feasibility:
            # No feasible slot for any unassociated practice
            return None

        practice_feasibility.sort(key=lambda x: x[1])
        most_constrained_practice = practice_feasibility[0][0]

        # Place it in the best slot available
        new_sol = self.place_item_with_lowest_penalty(most_constrained_practice, current_solution, self.practice_slots)
        return new_sol

    def expand_node(self, node):
        progress_state["expanded_nodes"] += 1
        self.logger.debug("Expanding node. Expanded count: %d", progress_state['expanded_nodes'])

        if node.is_pruned:
            return

        if self.is_solution_complete(node.solution):
            return
        
        # Identify if we have a baseline solution
        have_baseline = (self.best_solution is not None)

        # Identify unassigned games
        unassigned_games = [g for g in self.games if not any(g in assigns for assigns in node.solution.values())]

        # Separate late division games from others
        late_div_games = [g for g in unassigned_games if g.division > 90]
        if late_div_games:
            games_to_consider = late_div_games
        else:
            new_sol = self.place_unassociated_practices_first(node.solution)
            if new_sol is not None:
                node.solution = new_sol
            games_to_consider = unassigned_games

        # Most constrained game
        best_game = None
        best_valid_count = float('inf')
        valid_assignments_by_game = {}
        for g in games_to_consider:
            valid_slots = []
            for slot in self.game_slots:
                hypo = self.get_hypothetical_solution(g, slot, node.solution)
                if hypo and self.check_hard_constraints(hypo):
                    valid_slots.append(slot)
            valid_assignments_by_game[g] = valid_slots
            if 0 < len(valid_slots) < best_valid_count:
                best_valid_count = len(valid_slots)
                best_game = g

        if not best_game:
            node.is_pruned = True
            return

        # Just pick the first feasible slot for the best_game
        for slot in valid_assignments_by_game[best_game]:
            hypo = self.get_hypothetical_solution(best_game, slot, node.solution)
            if hypo and self.check_hard_constraints(hypo):
                assigned_sol = self.assign_associated_practices_greedily(best_game, hypo)
                if assigned_sol and self.check_hard_constraints(assigned_sol):
                    # After placing this game and its associated practices
                    # If complete, check improvement
                    if self.is_solution_complete(assigned_sol):
                        score = soft_penalty(assigned_sol, self.weights, self.preferences, self.pairs)
                        if score < progress_state["best_score"]:
                            child = ANDTreeNode(solution=assigned_sol, parent=node)
                            node.add_child(child)
                    else:
                        # Post-baseline pruning at node addition:
                        if have_baseline:
                            # Compute partial penalty
                            pscore = partial_soft_penalty(assigned_sol, self.weights, self.preferences, self.pairs)
                            if pscore >= progress_state["best_score"]:
                                # Skip adding this child entirely
                                continue
                        # If we reach here, either no baseline or pscore < best_score
                        child = ANDTreeNode(solution=assigned_sol, parent=node)
                        node.add_child(child)

                    # If we don't have a baseline solution yet, break after first successful child.
                    # if not have_baseline:
                    #     break


    def depth_first_search(self, node, visited_states=None, max_depth=1000, current_depth=0):
        # Perform a DFS from the given node, exploring children and pruning.
        # We keep track of visited states to avoid cycles or repeated expansions.
        if visited_states is None:
            visited_states = set()

        if node.is_pruned or current_depth >= max_depth:
            return

        # Re-check baseline at each call
        have_baseline = (self.best_solution is not None)

        state_items = []
        for slot in sorted(node.solution.keys(), key=lambda s: (s.day, s.start_time, s.id)):
            assigned_ids = tuple(sorted(it.id for it in node.solution[slot]))
            state_items.append((slot.id, assigned_ids))
        current_state = tuple(state_items)

        if current_state in visited_states:
            self.logger.debug("State already visited, skipping.")
            return
        visited_states.add(current_state)

        # Always re-check best_score before expanding
        self.expand_node(node)

        # Update progress stats
        assigned_games_count = self.count_assigned_games(node.solution)
        assigned_practices_count = self.count_assigned_practices(node.solution)
        progress_state["assigned_games"] = assigned_games_count
        progress_state["assigned_practices"] = assigned_practices_count

        # If we found a complete solution here, check if it's better than current best
        if self.is_solution_complete(node.solution):
            score = soft_penalty(node.solution, self.weights, self.preferences, self.pairs)
            if score < progress_state["best_score"]:
                progress_state["best_score"] = score
                self.best_score = score
                self.best_solution = node.solution
                self.logger.debug("Found new baseline solution with score=%s", score)
                self.save_solution_to_file("final_solution.txt")
                # Now prune children given we have a baseline
                # If children exist, prune them here:
                self.prune_children_based_on_baseline(node)

        if not node.unexplored_children:
            return

        # Now that we might have a baseline, prune children again
        # This ensures that even if baseline was found in a sibling, we prune here too.
        children = node.unexplored_children
        children_scores = []
        for c in children:
            pscore = partial_soft_penalty(c.solution, self.weights, self.preferences, self.pairs)
            children_scores.append((c, pscore))
        children_scores.sort(key=lambda x: x[1])

        pruned_children = []
        for (child, pscore) in children_scores:
            # This re-check ensures we always use the updated best_score
            if pscore >= progress_state["best_score"]:
                child.is_pruned = True
                pruned_children.append(child)
                self.logger.debug("Pruned child with pscore=%s > best_score=%s", pscore, progress_state["best_score"])
            elif not self.check_hard_constraints(child.solution):
                child.is_pruned = True
                pruned_children.append(child)
                self.logger.debug("Pruned child due to hard constraints.")
            else:
                self.depth_first_search(child, visited_states, max_depth, current_depth+1)
                node.explored_children.append(child)

        for pc in pruned_children:
            if pc in node.unexplored_children:
                node.unexplored_children.remove(pc)

        # Update parent references if any
        if node.parent:
            node.parent.explored_children.append(node)

    def prune_children_based_on_baseline(self, node):
        if not node.unexplored_children:
            return
        pruned_children = []
        for c in node.unexplored_children:
            pscore = partial_soft_penalty(c.solution, self.weights, self.preferences, self.pairs)
            if pscore >= progress_state["best_score"] or not self.check_hard_constraints(c.solution):
                c.is_pruned = True
                pruned_children.append(c)
        for pc in pruned_children:
            if pc in node.unexplored_children:
                node.unexplored_children.remove(pc)


    def run_search(self):
        # Initialize best_score to infinity and start the progress monitor.
        progress_state["best_score"] = float('inf')
        
        monitor_thread = threading.Thread(target=progress_monitor, daemon=True)
        monitor_thread.start()
        visited_states = set()
        
        # Start DFS from the root node
        self.depth_first_search(self.root, visited_states)
        
        # Mark search as done and join monitor thread
        progress_state["done"] = True
        monitor_thread.join()
        
        self.save_solution_to_file("final_solution_2.txt")
        return self.best_solution, progress_state["best_score"]

    def save_solution_to_file(self, filename):
        # Once the search ends, save the best found solution to a file.
        if self.best_solution is None:
            with open(filename, 'w') as f:
                f.write("No valid solution found.\n")
            return

        result_strings = []
        line_width = 40  # Format solutions for nice alignment

        for slot, items in self.best_solution.items():
            for item in items:
                hours = int(slot.start_time)
                minutes = int((slot.start_time - hours)*60)
                time_str = f"{hours:02}:{minutes:02}"
                day = format_day(slot.day)

                if isinstance(item, Practice):
                    base_string = f"{item.league} {item.tier} DIV {item.division:02} {item.practice_type.upper()}"
                else:
                    base_string = f"{item.league} {item.tier} DIV {item.division:02}"

                separator = " : "
                remaining_space = line_width - len(base_string) - len(separator) - len(day) - len(time_str) - 2
                if remaining_space > 0:
                    base_string += " " * remaining_space

                formatted_string = f"{base_string}{separator}{day}, {time_str}"
                result_strings.append(formatted_string)

        result_strings.sort()
        with open(filename, 'w') as f:
            for line in result_strings:
                f.write(line + "\n")
            f.write(f"\nEval value: {progress_state['best_score']}\n")

def format_day(day):
    # Convert the day representation into a standardized format.
    if day == "MWF" or day == "MW":
        formatted_day = "MO"
    elif day == "TR":
        formatted_day = "TU"
    elif day == "FR" or day == "F":
        formatted_day = "FR"
    else:
        formatted_day = day
    return formatted_day

def test_run():
    # This test run uses a small_test input for quick sanity check.
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inputs", "small_test.txt")
    Wminfilled = 0
    Wpref = 0
    Wpair = 0
    Wsecdif = 1
    PENgamemin = 1
    PENpracticemin = 1
    PENnotpaired = 0
    PENsection = 5

    logger, listener = setup_logger("debug.log")

    weights = [Wminfilled, Wpref, Wpair, Wsecdif, PENgamemin, PENpracticemin, PENnotpaired, PENsection]
    parsed_data = read_input(file_path)

    search = ANDTreeSearch(
        games=parsed_data.games,
        practices=parsed_data.practices,
        game_slots=parsed_data.game_slots,
        practice_slots=parsed_data.practice_slots,
        incompatibilities=parsed_data.incompatibilities,
        partial_assignments=parsed_data.partial_assignments,
        weights=weights,
        preferences=parsed_data.preferences,
        pairs=parsed_data.pair,
        unwanted=parsed_data.unwanted,
        logger=logger
    )

    search.run_search()
    
    listener.stop()

def setup_logger(log_filename="debug.log"):
    # Configure logging to a file for debugging and analysis.
    log_queue = Queue()
    logger = logging.getLogger("SchedulerLogger")
    logger.setLevel(logging.DEBUG)

    queue_handler = logging.handlers.QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    listener = logging.handlers.QueueListener(log_queue, file_handler)
    listener.start()

    return logger, listener

def run_for_file(file_path, weights = [0, 0, 0, 1, 1, 1, 0, 5]):
    # Utility function to run the search for a given file and weights.
    parsed_data = read_input(file_path)

    logger, listener = setup_logger("debug.log")

    search = ANDTreeSearch(
        games=parsed_data.games,
        practices=parsed_data.practices,
        game_slots=parsed_data.game_slots,
        practice_slots=parsed_data.practice_slots,
        incompatibilities=parsed_data.incompatibilities,
        partial_assignments=parsed_data.partial_assignments,
        weights=weights,
        preferences=parsed_data.preferences,
        pairs=parsed_data.pair,
        unwanted=parsed_data.unwanted,
        logger=logger
    )

    best_solution, best_score = search.run_search()
    listener.stop()
    return best_solution, best_score

if __name__ == "__main__":

    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "inputs", "large_2.txt")
    cProfile.run('run_for_file(file_path, [1, 1, 1, 1, 1, 1, 1, 1])', sort='time')
    # Loop through hc1.txt to hc12.txt.
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # for i in range(1, 13):
    #     filename = f"hc{i}.txt"
    #     file_path = os.path.join(script_dir, "..", "inputs", filename)
    #     print(f"Running {filename}...")
    #     best_solution, best_score = run_for_file(file_path)


    #     # All other hc files should produce no valid solution found.
    #     if best_solution is not None:
    #         print(f"ERROR: {filename} found a solution when it shouldn't have.")
    #     else:
    #         print(f"{filename} correctly returned no valid solution found.")

    # # Define the test cases based on your known reference outputs and parameter settings
    # test_cases = [
    #     {
    #         "filename": "pairing.txt",
    #         "weights": [0, 0, 1, 0, 0, 0, 11, 0],  # [w_minfilled, w_pref, w_pair, w_secdiff, pengamemin, penpracticemin, pennotpaired, pensection]
    #         "expected_eval": 55,
    #     },
    #     {
    #         "filename": "minnumber.txt",
    #         "weights": [1, 0, 0, 0, 100, 100, 0, 10],
    #         "expected_eval": 0,
    #     },
    #     {
    #         "filename": "parallelpen.txt",
    #         "weights": [0, 0, 0, 1, 1, 1, 0, 5],
    #         "expected_eval": 5,
    #     },
    #     {
    #         "filename": "prefexamp.txt",
    #         "weights": [0, 1, 0, 0, 100, 100, 0, 100],
    #         "expected_eval": 30,  # Insert the expected value if known
    #     }
    # ]

    # # Assuming your files are in a directory ../inputs relative to this script
    # script_dir = os.path.dirname(os.path.abspath(__file__))

    # for test_case in test_cases:
    #     filename = test_case["filename"]
    #     weights = test_case["weights"]
    #     file_path = os.path.join(script_dir, "..", "inputs", filename)

    #     print(f"Running {filename} with weights={weights}...")
    #     best_solution, best_score = run_for_file(file_path, weights)

    #     if best_solution is None:
    #         print(f"No valid solution found for {filename}.")
    #     else:
    #         print(f"Solution found for {filename} with Eval-value: {best_score}")

    #         # If you have an expected_eval value, compare it
    #         expected_eval = test_case.get("expected_eval")
    #         if expected_eval is not None:
    #             if best_score == expected_eval:
    #                 print(f"{filename}: Eval value matches expected result ({expected_eval}).")
    #             else:
    #                 print(f"{filename}: Eval value ({best_score}) does NOT match expected ({expected_eval}).")

    #     print()  # Blank line for readability
    
    
    # import argparse
    # parser = argparse.ArgumentParser(description="Process and calculate scores based on weights and penalties.")
    # parser.add_argument("filename", type=str, help="The file to process.")
    # parser.add_argument("wminfilled", type=float, help="Weight for minimal filled sections.")
    # parser.add_argument("wpref", type=float, help="Weight for preferred options.")
    # parser.add_argument("wpair", type=float, help="Weight for paired options.")
    # parser.add_argument("wsecdiff", type=float, help="Weight for section differences.")
    # parser.add_argument("pengamemin", type=float, help="Penalty for engagement minimum not met.")
    # parser.add_argument("penpracticemin", type=float, help="Penalty for practice minimum not met.")
    # parser.add_argument("pennotpaired", type=float, help="Penalty for not paired sections.")
    # parser.add_argument("pensection", type=float, help="Penalty for an entire section issue.")

    # # Parse arguments
    # args = parser.parse_args()

    # file_path = args.filename
    # Wminfilled = args.wminfilled
    # Wpref = args.wpref
    # Wpair = args.wpair
    # Wsecdif = args.wsecdiff
    # PENgamemin = args.pengamemin
    # PENpracticemin = args.penpracticemin
    # PENnotpaired = args.pennotpaired
    # PENsection = args.pensection

    # weights =  [Wminfilled, Wpref, Wpair, Wsecdif, PENgamemin, PENpracticemin, PENnotpaired, PENsection]

    # parsed_data = read_input(file_path)

    # search = ANDTreeSearch(
    #     games=parsed_data.games,
    #     practices=parsed_data.practices,
    #     game_slots=parsed_data.game_slots,
    #     practice_slots=parsed_data.practice_slots,
    #     incompatibilities=parsed_data.incompatibilities,
    #     partial_assignments=parsed_data.partial_assignments,
    #     weights=weights,
    #     preferences=parsed_data.preferences,
    #     pairs=parsed_data.pair,
    #     unwanted=parsed_data.unwanted,
    # )

    # search.run_search()