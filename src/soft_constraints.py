from models import GameSlot, PracticeSlot, Game, Practice
from hard_constraints import is_matching_day

def min_filled(solution, weights, preferences, pairs, item_preferences=None, pairs_map=None):
    # This soft constraint aims to encourage filling slots to their minimum desired count.
    #
    # Steps:
    # 1) Identify any game slots with fewer games than their gamemin.
    # 2) Identify any practice slots with fewer practices than their practicemin.
    # For each missing game or practice, add the appropriate penalty.
    #
    # Wminfilled is the global weight for this constraint,
    # PENgamemin and PENpracticemin are per-missing-item penalties.
    Wminfilled = weights[0]
    PENgamemin = weights[4]
    PENpracticemin = weights[5]

    occurrences_games = 0
    occurrences_practice = 0
    for slot, assignments in solution.items():
        c = len(assignments)
        if isinstance(slot, GameSlot) and c < slot.gamemin:
            occurrences_games += (slot.gamemin - c)
        if isinstance(slot, PracticeSlot) and c < slot.practicemin:
            occurrences_practice += (slot.practicemin - c)

    return (occurrences_games * PENgamemin + occurrences_practice * PENpracticemin) * Wminfilled

def preferences(solution, weights, preferences, pairs, item_preferences=None, pairs_map=None):
    Wpref = weights[1]
    penalty = 0

    # Build a dictionary: item_pref_map[item] = [(pday, ptime, pval), ...]
    # If item_preferences is None, we have to construct this map from preferences.
    if item_preferences is None:
        item_pref_map = {}
        for p in preferences:
            item = p.game_or_practice
            pday = p.slot_day
            ptime = p.slot_time
            pval = float(p.preference_value)
            if item not in item_pref_map:
                item_pref_map[item] = []
            item_pref_map[item].append((pday, ptime, pval))
    else:
        # item_preferences likely provides a single (pday, ptime, pval) per item
        # Convert that to a list for uniform handling.
        item_pref_map = {}
        for item, (pday, ptime, pval) in item_preferences.items():
            item_pref_map[item] = [(pday, ptime, pval)]

    # Now each item can have multiple preferences.
    # We add a penalty for each preference that isn't matched by the assigned slot.
    for slot, assignments in solution.items():
        sday, stime = slot.day, slot.start_time
        for item in assignments:
            if item in item_pref_map:
                # Check all preferences for this item
                for (pday, ptime, pval) in item_pref_map[item]:
                    if pday != sday or abs(ptime - stime) > 1e-9:
                        penalty += Wpref * pval

    return penalty


def paired(solution, weights, preferences, pairs, item_preferences=None, pairs_map=None):
    # This soft constraint deals with pairs of items that should be assigned simultaneously.
    #
    # Steps:
    # 1) Record the slot of each assigned item.
    # 2) For each pair in 'pairs', check if both items are assigned to the same day/time slot.
    # 3) If not matched, add a penalty (Wpair * PENnotpaired) for each unmatched pair.
    Wpair = weights[2]
    PENnotpaired = weights[6]

    total_pairs = len(pairs)
    if total_pairs == 0:
        return 0

    # Map each assigned item to its slot
    item_slot = {}
    for slot, assignments in solution.items():
        for it in assignments:
            item_slot[it] = slot

    matched = 0
    for pair_obj in pairs:
        i1, i2 = pair_obj.game_or_practice1, pair_obj.game_or_practice2
        s1 = item_slot.get(i1)
        s2 = item_slot.get(i2)
        if s1 and s2 and is_matching_day(s1.day, s2.day) and abs(s1.start_time - s2.start_time) < 1e-9:
            matched += 1

    # Penalty for each unmatched pair
    return (total_pairs - matched)*Wpair*PENnotpaired

def sec_diff(solution, weights, preferences, pairs, item_preferences=None, pairs_map=None):
    # This constraint imposes penalties when multiple items of the same league and tier
    # but different divisions appear together in the same slot.
    #
    # For each slot, if we find two items with same league/tier but different division,
    # add PENsection for each such pair. Multiply total by Wsecdif.
    Wsecdif = weights[3]
    PENsection = weights[7]
    divisional_penalty = 0
    for slot, assignments in solution.items():
        count = len(assignments)
        for i in range(count):
            it1 = assignments[i]
            for j in range(i+1, count):
                it2 = assignments[j]
                if (it1.league == it2.league and it1.tier == it2.tier and it1.division != it2.division):
                    divisional_penalty += PENsection
    return divisional_penalty * Wsecdif

def return_finished_soft_constraint_list():
    # Return the list of soft constraints that should be applied to the final (complete) solution
    # This includes all constraints that make sense after all assignments are made.
    return [min_filled, preferences, paired, sec_diff]

def return_partial_soft_constraint_list():
    # Return the list of soft constraints that can be applied partially, even before the solution is complete.
    # These help guide the search towards better partial solutions.
    return [preferences, paired, sec_diff]

def soft_penalty(solution, weights, preferences, pairs, item_preferences=None, pairs_map=None):
    # Compute the total penalty for a fully assigned solution using all finished constraints.
    penalty = 0
    for constraint in return_finished_soft_constraint_list():
        penalty += constraint(solution, weights, preferences, pairs, item_preferences, pairs_map)
    return penalty

def partial_soft_penalty(solution, weights, preferences, pairs, item_preferences=None, pairs_map=None):
    # Compute a partial penalty for a partially assigned solution using a subset of constraints
    # This helps guide the search towards better solutions, even when incomplete.
    penalty = 0
    for constraint in return_partial_soft_constraint_list():
        penalty += constraint(solution, weights, preferences, pairs, item_preferences, pairs_map)
    return penalty