from models import Game, GameSlot, PracticeSlot

def separate_slots(solution):
    # Separate game and practice slots for easier application of slot-specific constraints.
    game_slots = {slot: assigns for slot, assigns in solution.items() if isinstance(slot, GameSlot)}
    practice_slots = {slot: assigns for slot, assigns in solution.items() if isinstance(slot, PracticeSlot)}
    return game_slots, practice_slots

# Use bitmasks for day matching to avoid multiple condition checks each call.
DAY_CODES = {
    "MWF": 0b111,
    "MW":  0b110,
    "F":   0b001,
    "TR":  0b010,
    "TU":  0b100
}

def is_matching_day(day1, day2):
    # Two patterns match if their bitmasks share any common bit.
    return (DAY_CODES[day1] & DAY_CODES[day2]) != 0

def game_capacity(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Ensure no game slot exceeds its gamemax capacity.
    for slot, assignments in game_slots.items():
        if len(assignments) > slot.gamemax:
            return False
    return True

def practice_capacity(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Ensure no practice slot exceeds its practicemax capacity.
    for slot, assignments in practice_slots.items():
        if len(assignments) > slot.practicemax:
            return False
    return True

def overlapping_games_practices(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Check that games and practices of the same division do not improperly overlap.
    game_lookup = {}
    for gs, gassign in game_slots.items():
        for g in gassign:
            key = (g.league, g.tier, g.division)
            game_lookup.setdefault(key, []).append(gs)

    for ps, passign in practice_slots.items():
        for p in passign:
            key = (p.league, p.tier, p.division)
            if key not in game_lookup:
                continue
            for gs in game_lookup[key]:
                if is_matching_day(gs.day, ps.day) and gs.start_time < ps.end_time and ps.start_time < gs.end_time:
                    return False
    return True

def late_divisions(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Divisions 90-99 must not start before 17:00.
    for slot, assignments in solution.items():
        s_start = slot.start_time
        for item in assignments:
            div = item.division
            if 90 <= div < 100 and s_start < 18.0:
                return False
    return True

def overlapping_tiers(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Ensure no slot contains more than one item with 'has_overlapping_tier'.
    for slot, assignments in solution.items():
        overlap_items = [it for it in assignments if getattr(it, 'has_overlapping_tier', False)]
        if len(overlap_items) > 1:
            return False
    return True

def no_tuesday_eleven(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # No games on TR between 11:00 and 12:30.
    for gs, gassign in game_slots.items():
        if gs.day == "TR" and 11.0 <= gs.start_time < 12.5 and gassign:
            return False
    return True

def cmsa_tuesday(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Certain CMSA tiers require practices on TU between 18:00 and 19:00.
    required_tiers = {"U12T1S", "U13T1S"}
    required_league = "CMSA"
    for ps, passign in practice_slots.items():
        s_day, s_start = ps.day, ps.start_time
        meets_time = (s_day == "TU" and 18.0 <= s_start < 19.0)
        for item in passign:
            if item.league == required_league and item.tier in required_tiers:
                if not meets_time:
                    return False
    return True

def cmsa_overlapping_tiers(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Certain CMSA tiers must not overlap.
    cannot_overlap = {("U12T1", "U12T1S"), ("U13T1", "U13T1S")}
    required_league = "CMSA"
    for (tier1, tier2) in cannot_overlap:
        for gs, gassign in game_slots.items():
            relevant_games = [g for g in gassign if g.league == required_league and g.tier == tier1]
            if not relevant_games:
                continue
            for ps, passign in practice_slots.items():
                if is_matching_day(gs.day, ps.day) and ps.start_time < gs.end_time and gs.start_time < ps.end_time:
                    for pitem in passign:
                        if pitem.league == required_league and pitem.tier == tier2:
                            return False
    return True

def check_u15_u19_non_overlapping(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
    # Ensure no more than one U15/U16/U17/U19 game in the same slot.
    for slot, assignments in solution.items():
        count = 0
        for it in assignments:
            if isinstance(it, Game) and any(t in it.tier for t in ["U15", "U16", "U17", "U19"]):
                count += 1
                if count > 1:
                    return False
    return True

def satisfies_hard_constraints(solution, incompatibilities_list, unwanted_list, incompat_map):
    # Check all defined constraints in order.
    game_slots, practice_slots = separate_slots(solution)

    # Intra-slot incompatibilities
    for slot, assignments in solution.items():
        count = len(assignments)
        for i in range(count):
            it1 = assignments[i]
            if it1 in incompat_map:
                incs = incompat_map[it1]
                for it2 in assignments[i+1:]:
                    if it2 in incs:
                        return False

    # Inter-slot incompatibilities
    for gs, gassign in game_slots.items():
        gs_day, gs_start, gs_end = gs.day, gs.start_time, gs.end_time
        for ps, passign in practice_slots.items():
            if is_matching_day(gs_day, ps.day) and ps.start_time < gs_end and gs_start < ps.end_time:
                for gitem in gassign:
                    if gitem in incompat_map:
                        incs = incompat_map[gitem]
                        for pitem in passign:
                            if pitem in incs:
                                return False

    # Unwanted assignments
    for unwant in unwanted_list:
        uw_day, uw_time, uw_id = unwant.slot_day, unwant.slot_time, unwant.game_or_practice.id
        for slot, assignments in solution.items():
            if slot.day == uw_day and abs(slot.start_time - uw_time) < 1e-9:
                for item in assignments:
                    if item.id == uw_id:
                        return False

    # Apply other constraints in sequence.
    for constraint in [
        game_capacity,
        practice_capacity,
        overlapping_games_practices,
        late_divisions,
        no_tuesday_eleven,
        overlapping_tiers,
        cmsa_tuesday,
        cmsa_overlapping_tiers,
        check_u15_u19_non_overlapping
    ]:
        if not constraint(solution, incompatibilities_list, unwanted_list, game_slots, practice_slots):
            return False

    return True