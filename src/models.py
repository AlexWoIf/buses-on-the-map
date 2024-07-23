import json
from dataclasses import asdict, dataclass


@dataclass
class WindowBounds:
    south_lat: float = None
    north_lat: float = None
    west_lng: float = None
    east_lng: float = None
    error: str = ''

    def update(self, new_bounds):
        self.west_lng = new_bounds['west_lng']
        self.east_lng = new_bounds['east_lng']
        self.south_lat = new_bounds['south_lat']
        self.north_lat = new_bounds['north_lat']


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str

    def is_inside(self, bounds):
        initialized = True
        for bound in asdict(bounds).values():
            initialized = initialized and bound is not None
        if not initialized:
            return False
        return (bounds.south_lat < self.lat < bounds.north_lat and 
                bounds.west_lng < self.lng < bounds.east_lng)
