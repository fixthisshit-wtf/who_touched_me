from .http_receiver import start_server

DOMAIN = "who_touched_me"

def setup(hass, config):
    start_server(hass)
    return True
