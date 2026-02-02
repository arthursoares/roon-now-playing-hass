"""Constants for the Roon Now Playing integration."""
from typing import Final

DOMAIN: Final = "roon_now_playing"

# Platforms
PLATFORMS: Final = ["select", "binary_sensor"]

# Configuration
CONF_HOST: Final = "host"

# Defaults
DEFAULT_PORT: Final = 3000

# Options for select entities (mirrored from roon-now-playing server)
LAYOUTS: Final = [
    "detailed",
    "minimal",
    "fullscreen",
    "ambient",
    "cover",
    "facts-columns",
    "facts-overlay",
    "facts-carousel",
    "basic",
]

FONTS: Final = [
    "system",
    "patua-one",
    "comfortaa",
    "noto-sans-display",
    "coda",
    "bellota-text",
    "big-shoulders",
    "inter",
    "roboto",
    "open-sans",
    "lato",
    "montserrat",
    "poppins",
    "source-sans-3",
    "nunito",
    "raleway",
    "work-sans",
]

BACKGROUNDS: Final = [
    "black",
    "white",
    "dominant",
    "gradient-radial",
    "gradient-linear",
    "gradient-linear-multi",
    "gradient-radial-corner",
    "gradient-mesh",
    "blur-subtle",
    "blur-heavy",
    "duotone",
    "posterized",
    "gradient-noise",
    "blur-grain",
]
