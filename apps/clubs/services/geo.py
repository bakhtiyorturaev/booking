import math


def haversine_km(latitude_a, longitude_a, latitude_b, longitude_b):
    radius = 6371.0088
    lat_a = math.radians(float(latitude_a))
    lat_b = math.radians(float(latitude_b))
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(float(longitude_b) - float(longitude_a))
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
