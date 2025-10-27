"""Constants for WhoTouchedMe integration."""

DOMAIN = "who_touched_me"
DEFAULT_PORT = 9123
DEFAULT_HOST = "0.0.0.0"

# Configuration keys
CONF_PORT = "port"
CONF_SECRET_TOKEN = "secret_token"
CONF_MAPPING = "mapping"

# Platforms
PLATFORMS = ["sensor", "select"]

# Finger index to name mapping (ekey bionyx API standard)
# Negative values = left hand, positive values = right hand
FINGER_MAPPING = {
    -5: "left_little_finger",
    -4: "left_ring_finger",
    -3: "left_middle_finger",
    -2: "left_index_finger",
    -1: "left_thumb",
    0: "none",
    1: "right_thumb",
    2: "right_index_finger",
    3: "right_middle_finger",
    4: "right_ring_finger",
    5: "right_little_finger",
}

# All possible finger options for SelectEntity
FINGER_OPTIONS = [
    "none",
    "right_thumb",
    "right_index_finger",
    "right_middle_finger",
    "right_ring_finger",
    "right_little_finger",
    "left_thumb",
    "left_index_finger",
    "left_middle_finger",
    "left_ring_finger",
    "left_little_finger",
]

# Result codes from ekey API
RESULT_CODES = {
    10: "match",
    20: "filtered_match",
    30: "no_match",
    0: "unknown",
}

# Type codes from ekey API
TYPE_CODES = {
    10: "finger",
    20: "digital_input",
}

# Detail codes from ekey API
DETAIL_CODES = {
    10: "input_disabled",
    20: "schedule",
    30: "no_rule",
    40: "no_input",
    50: "invalid_input",
    60: "time_limitation",
}