from calendar import day_abbr
import re

class Game:
    def __init__(self, identifier, league, tier, division):
        self.id = identifier
        self.league = league
        self.tier = tier
        self.division = int(division)
        # Precompute a key tuple for quick comparison
        self._eq_key = (self.id, self.league, self.tier, self.division)

    def __eq__(self, other):
        if not isinstance(other, Game):
            return NotImplemented
        return self._eq_key == other._eq_key

    def __hash__(self):
        # Use tuple hashing to ensure unique hash for each game combination.
        return hash((self.id, self.league, self.tier, self.division))

class Practice:
    def __init__(self, identifier, league, tier, division, practice_type):
        self.id = identifier
        self.league = league
        self.tier = tier
        self.division = int(division)
        self.practice_type = practice_type
        # For the wildcard division, precompute a key without division first:
        self._base_eq_key = (self.id, self.league, self.tier, self.practice_type)

    def __eq__(self, other):
        if not isinstance(other, Practice):
            return NotImplemented
        # Check base equality quickly first
        if self._base_eq_key != other._base_eq_key:
            return False
        # Only if base match, handle division logic
        return (self.division == 0 or other.division == 0 or self.division == other.division)
    
    def __hash__(self):
        # Use 0 for division in the hash to match the equality rule.
        # This ensures that practices differing only by their division number still hash consistently.
        return hash((self.id, self.league, self.tier, 0, self.practice_type))

def normalize_days(day_str, game_or_practice):
    # Convert an input day string (e.g., "MO", "TU") into a normalized day pattern.
    # Games and practices have different normalization rules:
    # - For a Game: "MO", "WE", or "FR" become "MWF". Other days become "TR".
    # - For a Practice: "MO" or "WE" -> "MW", "TU" or "TH" -> "TR", else "F".
    #
    # This standardizes day representations to a smaller set of patterns for easier comparison.
    if type(game_or_practice) == Game:
        if day_str == "MO" or day_str == "WE" or day_str == "FR":
            day_str = "MWF"
        else:
            day_str = "TR"
    else:
        # For a practice
        if day_str == "MO" or day_str == "WE":
            day_str = "MW"
        elif day_str == "TU" or day_str == "TH":
            day_str = "TR"
        else:
            day_str = "F"

    return day_str

def make_game_or_practice_obj(identifier, input_str):
    # Parse a string representation of a game or practice and return the corresponding object.
    # If the string contains "PRC" or "OPN", we treat it as a practice. Otherwise, it's a game.
    #
    # For games and practices, we strip out "DIV", normalize whitespace, and split the string into parts.
    # Then we extract league, tier, division, and practice_type (if applicable).
    if "PRC" in input_str or "OPN" in input_str:
        # This is a practice-type input
        normalized_string = input_str.replace("DIV", "").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        if "DIV" not in input_str:
            # If no explicit "DIV" found, set division=0
            league = parts[0]
            tier = parts[1]
            division = 0
            practice_type = f"{parts[2]} {parts[3]}"
        else:
            league = parts[0]
            tier = parts[1]
            division = parts[2]
            practice_type = f"{parts[3]} {parts[4]}"
        res_obj = Practice(
            identifier=identifier, league=league, tier=tier, division=division, practice_type=practice_type
        )
    else:
        # This is a game-type input
        normalized_string = input_str.replace("DIV", "").strip()
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        parts = normalized_string.split()
        league = parts[0]
        tier = parts[1]
        division = parts[2]
        res_obj = Game(identifier=identifier, league=league, tier=tier, division=division)

    return res_obj

class GameSlot:
    def __init__(self, identifier, day, start_time, gamemax, gamemin):
        # A GameSlot represents a slot allocated for games on certain days and times.
        # Adjust the day and end_time based on predefined rules:
        # - Monday -> "MWF" and duration of 1 hour
        # - Tuesday -> "TR" and duration of 1.5 hours
        #
        # Store gamemax/gamemin to ensure capacity constraints, and maintain a list of assigned games.
        self.id = identifier
        self.day, self.start_time, self.end_time = self.adjust_day_and_time(day, start_time)
        self.gamemax = int(gamemax)
        self.gamemin = int(gamemin)
        self.games = []

    @staticmethod
    def _convert_time_to_float(time_str):
        """
        Convert a time string like "10:30" into a float hour, e.g. 10.5.
        """
        hours, minutes = map(int, time_str.split(":"))
        return hours + minutes / 60.0

    def adjust_day_and_time(self, day, start_time):
        """
        Convert input day and start_time into normalized pattern and compute end_time.
        For games:
        - MO -> MWF + 1 hour
        - TU -> TR + 1.5 hours
        """
        adjusted_day = None
        end_time = None
        start_time_float = self._convert_time_to_float(start_time)
        if day == "MO":
            adjusted_day = "MWF"
            end_time = start_time_float + 1
        elif day == "TU":
            adjusted_day = "TR"
            end_time = start_time_float + 1.5
        else:
            print("Invalid Day:")
            print(day)

        return adjusted_day, start_time_float, end_time

class PracticeSlot:
    def __init__(self, identifier, day, start_time, practicemax, practicemin):
        # A PracticeSlot represents a slot allocated for practices.
        # Similar logic to GameSlot, but with different day-to-duration mappings:
        # MO or WE -> "MW" and +1 hour
        # TU -> "TR" and +1 hour
        # FR -> "F" and +2 hours
        #
        # Keep track of practicemax/practicemin for capacity checks.
        self.id = identifier
        self.day, self.start_time, self.end_time = self.adjust_day_and_time(day, start_time)
        self.practicemax = int(practicemax)
        self.practicemin = int(practicemin)
        self.practices = []

    @staticmethod
    def _convert_time_to_float(time_str):
        """
        Convert a time string like "10:30" into a float hour (e.g. 10.5).
        """
        hours, minutes = map(int, time_str.split(":"))
        return hours + minutes / 60.0
    
    def adjust_day_and_time(self, day, start_time):
        """
        Adjust the day and end_time for a practice slot:
        - MO or WE -> MW, +1 hour
        - TU -> TR, +1 hour
        - FR -> F, +2 hours
        """
        adjusted_day = None
        end_time = None
        start_time_float = self._convert_time_to_float(start_time)
        if day == "MO":
            adjusted_day = "MW"
            end_time = start_time_float + 1
        elif day == "TU":
            adjusted_day = "TR"
            end_time = start_time_float + 1
        elif day == "FR":
            adjusted_day = "F"
            end_time = start_time_float + 2
        else:
            print("Invalid Day:")
            print(day)

        return adjusted_day, start_time_float, end_time

class Preference:
    def __init__(self, identifier, slot_day, slot_time, game_or_practice, preference_value):
        # A Preference links a specific game/practice to a preferred slot (day/time).
        # Normalize the day, and store the time as a float.
        self.id = identifier
        self.slot_time = self._convert_time_to_float(slot_time)
        self.game_or_practice = game_or_practice
        self.preference_value = preference_value
        self.slot_day = normalize_days(day_str=slot_day, game_or_practice=self.game_or_practice)

    @staticmethod
    def _convert_time_to_float(time_str):
        """
        Convert "HH:MM" into a float hour representation.
        """
        hours, minutes = map(int, time_str.split(":"))
        return hours + minutes / 60.0

class PairConstraint:
    def __init__(self, identifier, game_or_practice1, game_or_practice2):
        # A PairConstraint specifies that two items should be scheduled at the same time.
        self.id = identifier
        self.game_or_practice1 = game_or_practice1
        self.game_or_practice2 = game_or_practice2

class Incompatible:
    def __init__(self, identifier, game_or_practice1, game_or_practice2):
        # An Incompatible pair means these two items cannot appear together at all,
        # or must not appear in the same slot (depending on interpretation).
        self.id = identifier
        self.game_or_practice1 = game_or_practice1
        self.game_or_practice2 = game_or_practice2

class Unwanted:
    def __init__(self, identifier, game_or_practice, slot_day, slot_time):
        # An Unwanted constraint specifies that a certain item must NOT be placed in a specific slot.
        # Normalize the day and convert the slot_time to float.
        self.id = identifier
        self.game_or_practice = game_or_practice
        self.slot_day = normalize_days(day_str=slot_day, game_or_practice=self.game_or_practice)
        self.slot_time = self._convert_time_to_float(slot_time)

    @staticmethod
    def _convert_time_to_float(time_str):
        """
        Convert "HH:MM" into a float hour representation.
        """
        hours, minutes = map(int, time_str.split(":"))
        return hours + minutes / 60.0

class PartialAssignments:
    def __init__(self, identifier, game_or_practice, slot_day, slot_time):
        # PartialAssignments specify that a certain item must be placed in a specific slot if possible.
        # Normalize the day and convert time to float.
        self.id = identifier
        self.game_or_practice = game_or_practice
        self.slot_day = normalize_days(day_str=slot_day, game_or_practice=self.game_or_practice)
        self.slot_time = self._convert_time_to_float(slot_time)

    @staticmethod
    def _convert_time_to_float(time_str):
        """
        Convert "HH:MM" into a float hour representation.
        """
        hours, minutes = map(int, time_str.split(":"))
        return hours + minutes / 60.0