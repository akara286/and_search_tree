import re
from models import Game, Practice, GameSlot, PracticeSlot, Unwanted, PartialAssignments, PairConstraint, Preference, Incompatible

class ParsedData:
    """
    A lightweight structure to pass parsed input data without tying it
    to any specific implementation details. This allows for flexible use
    after initial parsing.
    """
    def __init__(self, games, practices, game_slots, practice_slots, incompatibilities, unwanted, preferences, pair, partial_assignments):
        self.games = games
        self.practices = practices
        self.game_slots = game_slots
        self.practice_slots = practice_slots
        self.incompatibilities = incompatibilities
        self.unwanted = unwanted
        self.preferences = preferences
        self.pair = pair
        self.partial_assignments = partial_assignments

def read_input(filename):
    """
    Reads the input file and transforms raw textual data into structured objects.
    
    Expected sections:
    - Game slots:
    - Practice slots:
    - Games:
    - Practices:
    - Not compatible:
    - Unwanted:
    - Preferences:
    - Pair:
    - Partial assignments:
    
    Each section is read until a blank line or EOF. After reading all sections,
    the data is organized into typed objects for easy use in the scheduling logic.
    """
    game_slots = []
    practice_slots = []
    games = []
    practices = []
    not_compatible = []
    unwanted = []
    preferences = []
    pair = []
    partial_assignments = []

    try:
        with open(filename, 'r') as file:
            while True:
                line = file.readline()
                if not line:
                    break

                # Detect sections by keywords
                if "Game slots:" in line:
                    read_section(file, game_slots)

                elif "Practice slots:" in line:
                    read_section(file, practice_slots)

                elif "Games:" in line:
                    read_section(file, games)

                elif "Practices:" in line:
                    read_section(file, practices)

                elif "Not compatible:" in line:
                    read_section(file, not_compatible)

                elif "Unwanted:" in line:
                    read_section(file, unwanted)

                elif "Preferences:" in line:
                    read_section(file, preferences)

                elif "Pair:" in line:
                    read_section(file, pair)

                elif "Partial assignments:" in line:
                    read_section(file, partial_assignments)
                    # After partial assignments, input ends
                    break

    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{filename}' not found.")
    except Exception as e:
        raise Exception(f"Error reading the input file: {e}")

    # Convert raw lists into structured objects
    game_objects, special_practice_object = organize_game_objects(games)
    practice_objects = organize_practice_objects(practices) + special_practice_object
    game_slot_objects = organize_game_slot_objects(game_slots)
    practice_slot_objects = organize_practice_slot_objects(practice_slots)
    pair_objects = organize_pair_objects(pair, game_objects, practice_objects)
    preferences_objects = organize_preferences_objects(preferences, game_objects, practice_objects)
    unwanted_objects = organize_unwanted_objects(unwanted, game_objects, practice_objects)
    partial_assignment_objects = organize_partial_assignment_objects(partial_assignments, game_objects, practice_objects)
    incompatible_objects = organize_incompatible_objects(not_compatible, game_objects, practice_objects)

    return ParsedData(
        games=game_objects,
        practices=practice_objects,
        game_slots=game_slot_objects,
        practice_slots=practice_slot_objects,
        incompatibilities=incompatible_objects,
        unwanted=unwanted_objects,
        preferences=preferences_objects,
        pair=pair_objects,
        partial_assignments=partial_assignment_objects,
    )

def determine_game_or_practice(game_or_practice, game_objects, practice_objects):
    """
    Given a raw string describing a game or practice, find the corresponding 
    object from game_objects or practice_objects. This function first parses 
    the string to identify if it's a practice or a game, then searches 
    through the provided lists to find a matching object.
    """
    if "OPN" in game_or_practice or "PRC" in game_or_practice:
        # Treat as practice
        normalized_string = game_or_practice.replace("DIV", "").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        # If DIV not mentioned, division=0 (wildcard division)
        if "DIV" not in game_or_practice:
            league = parts[0]
            tier = parts[1]
            division = 0
            practice_type = f"{parts[2]} {parts[3]}"
        else:
            league = parts[0]
            tier = parts[1]
            division = parts[2]
            practice_type = f"{parts[3]} {parts[4]}"

        # Find matching practice in practice_objects
        identifier = None
        for practice in practice_objects:
            if (practice.league == league and practice.tier == tier and 
                practice.division == int(division) and practice.practice_type == practice_type):
                identifier = practice.id
                break
        res = Practice(identifier=identifier, league=league, tier=tier, division=division, practice_type=practice_type)

    else:
        # Treat as game
        normalized_string = game_or_practice.replace("DIV", "").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        league = parts[0]
        tier = parts[1]
        division = parts[2]
        # Find matching game in game_objects
        identifier = None
        for game in game_objects:
            if game.league == league and game.tier == tier and game.division == int(division):
                identifier = game.id
                break
        res = Game(identifier=identifier, league=league, tier=tier, division=division)

    return res

def organize_incompatible_objects(not_compatibles:list, game_objects, practice_objects):
    """
    Convert raw 'Not compatible:' lines into Incompatible objects.
    Each line typically specifies two items that can't appear together.
    """
    incompatible_object_list = []

    for i, item in enumerate(not_compatibles):
        normalized_string = re.sub(r'\s+', ' ', item)
        parts = [part.strip() for part in normalized_string.split(",")]
        game_or_practice1 = determine_game_or_practice(parts[0], game_objects, practice_objects)
        game_or_practice2 = determine_game_or_practice(parts[1], game_objects, practice_objects)
        incompatible_obj = Incompatible(identifier=i, game_or_practice1=game_or_practice1, game_or_practice2=game_or_practice2)
        incompatible_object_list.append(incompatible_obj)

    return incompatible_object_list

def organize_pair_objects(pairs: list, game_objects, practice_objects):
    """
    Convert raw 'Pair:' lines into PairConstraint objects.
    Each pair line contains two items that should be scheduled at the same time.
    """
    pair_list = []

    for i, pair_cst in enumerate(pairs):
        normalized_string = re.sub(r'\s+', ' ', pair_cst)
        parts = [part.strip() for part in normalized_string.split(",")]
        game_or_practice1 = determine_game_or_practice(parts[0], game_objects, practice_objects)
        game_or_practice2 = determine_game_or_practice(parts[1], game_objects, practice_objects)
        pair_obj = PairConstraint(identifier=i, game_or_practice1=game_or_practice1, game_or_practice2=game_or_practice2)
        pair_list.append(pair_obj)

    return pair_list

def organize_preferences_objects(preferences_list: list, game_objects, practice_objects):
    """
    Convert raw 'Preferences:' lines into Preference objects.
    Each preference line maps an item to a preferred slot (day/time) and a preference value.
    """
    preference_obj_list = []

    for i, preference in enumerate(preferences_list):
        normalized_string = re.sub(r'\s+', ' ', preference)
        parts = [part.strip() for part in normalized_string.split(",")]
        slot_day = parts[0]
        slot_time = parts[1]
        game_or_practice = determine_game_or_practice(parts[2], game_objects, practice_objects)
        preference_value = parts[3]
        preference_obj = Preference(
            identifier=i, slot_day=slot_day, slot_time=slot_time,
            game_or_practice=game_or_practice, preference_value=preference_value
        )
        preference_obj_list.append(preference_obj)

    return preference_obj_list

def organize_partial_assignment_objects(partial_list: list, game_objects, practice_objects):
    """
    Convert raw 'Partial assignments:' lines into PartialAssignments objects.
    Each partial assignment fixes an item to a specific slot if possible.
    """
    partial_obj_list = []

    for i, partial in enumerate(partial_list):
        normalized_string = re.sub(r'\s+', ' ', partial)
        parts = [part.strip() for part in normalized_string.split(",")]
        game_or_practice = determine_game_or_practice(parts[0], game_objects, practice_objects)
        slot_day = parts[1]
        slot_time = parts[2]
        partial_obj = PartialAssignments(identifier=i, game_or_practice=game_or_practice, slot_day=slot_day, slot_time=slot_time)
        partial_obj_list.append(partial_obj)

    return partial_obj_list

def organize_unwanted_objects(unwanted_list: list, game_objects, practice_objects):
    """
    Convert raw 'Unwanted:' lines into Unwanted objects.
    Each line specifies an item that should not be placed in a given slot.
    """
    unwanted_obj_list = []

    for i, unw in enumerate(unwanted_list):
        normalized_string = re.sub(r'\s+', ' ', unw)
        parts = [part.strip() for part in normalized_string.split(",")]
        game_or_practice = determine_game_or_practice(parts[0], game_objects, practice_objects)
        slot_day = parts[1]
        slot_time = parts[2]
        unwanted_obj = Unwanted(identifier=i, game_or_practice=game_or_practice, slot_day=slot_day, slot_time=slot_time)
        unwanted_obj_list.append(unwanted_obj)

    return unwanted_obj_list

def organize_game_slot_objects(game_slots: list):
    """
    Convert raw 'Game slots:' lines into GameSlot objects.
    Each line typically contains day, start_time, gamemax, gamemin.
    """
    game_slot_obj_list = []

    for i, slot in enumerate(game_slots):
        normalized_string = slot.replace(",", " ").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        day = parts[0]
        start_time = parts[1]
        game_max = parts[2]
        game_min = parts[3]
        game_obj = GameSlot(identifier=i, day=day, start_time=start_time, gamemax=game_max, gamemin=game_min)
        game_slot_obj_list.append(game_obj)

    return game_slot_obj_list

def organize_practice_slot_objects(practice_slots: list):
    """
    Convert raw 'Practice slots:' lines into PracticeSlot objects.
    Each line should have day, start_time, practicemax, practicemin.
    """
    practice_slot_obj_list = []

    for i, slot in enumerate(practice_slots):
        normalized_string = slot.replace(",", " ").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        day = parts[0]
        start_time = parts[1]
        practice_max = parts[2]
        practice_min = parts[3]
        game_obj = PracticeSlot(identifier=i, day=day, start_time=start_time, practicemax=practice_max, practicemin=practice_min)
        practice_slot_obj_list.append(game_obj)

    return practice_slot_obj_list

def organize_game_objects(games_list: list):
    """
    Convert raw 'Games:' lines into Game objects.
    Additionally, if certain tiers (e.g., U12T1, U13T1) require associated special practices,
    create a special practice object and include it separately.
    """
    games_obj_list = []
    practice_obj_list = []

    for i, game in enumerate(games_list):
        normalized_string = game.replace("DIV", "").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        league = parts[0]
        tier = parts[1]
        division = parts[2]
        game_obj = Game(identifier=i, league=league, tier=tier, division=division)
        games_obj_list.append(game_obj)

        if tier in ["U12T1", "U13T1"]:
            # Some special logic to create a corresponding practice with a "S" tier (e.g., U13T1S)
            spec_tier = f"{tier}S"
            special_prac = Practice(identifier=0, league="CMSA", tier=spec_tier, division=division, practice_type="")
            practice_obj_list.append(special_prac)

    return games_obj_list, practice_obj_list

def organize_practice_objects(practice_list: list):
    """
    Convert raw 'Practices:' lines into Practice objects.
    If no explicit DIV is mentioned, set division=0 (wildcard).
    """
    practice_obj_list = []

    for i, practice in enumerate(practice_list):
        if "DIV" not in practice:
            # If DIV not specified, division=0
            normalized_string = practice.replace("DIV", "").strip()
            normalized_string = re.sub(r'\s+', ' ', normalized_string)
            parts = normalized_string.split()
            league = parts[0]
            tier = parts[1]
            division = 0
            practice_type = f"{parts[2]} {parts[3]}"
            practice_obj = Practice(
                identifier=i, league=league, tier=tier, division=division, practice_type=practice_type
            )
            practice_obj_list.append(practice_obj)
        else:
            normalized_string = practice.replace("DIV", "").strip()
            normalized_string = re.sub(r'\s+', ' ', normalized_string)
            parts = normalized_string.split()
            league = parts[0]
            tier = parts[1]
            division = parts[2]
            practice_type = f"{parts[3]} {parts[4]}"
            practice_obj = Practice(identifier=i, league=league, tier=tier, division=division, practice_type=practice_type)
            practice_obj_list.append(practice_obj)

    return practice_obj_list

def read_section(file, target_list):
    """
    Reads a section of the input until an empty line or EOF and appends each line to target_list.
    Sections are expected to be continuously listed until a blank line indicates section end.
    """
    while True:
        line = file.readline().strip()
        if not line:
            break
        target_list.append(line)

def parse_not_compatible(not_compatible):
    """
    Convert raw 'Not compatible:' lines into a quick lookup dictionary.
    Not currently used if we have a direct structure, but provides a fallback map.
    """
    incompatibilities = {}
    for entry in not_compatible:
        items = [item.strip() for item in entry.split(",")]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i] not in incompatibilities:
                    incompatibilities[items[i]] = set()
                incompatibilities[items[i]].add(items[j])
    return incompatibilities