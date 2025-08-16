import random
import colorama.ansi as a


# Print red tekst in console for debug
def printc(text: str, color: a.AnsiFore = a.AnsiFore.RED):
    return print(a.Fore.RED + repr(text) + a.Fore.RESET)


# Generate random coordinates
def get_random_coordinates(latitude=52.40833333333333, longitude=16.93333333333333):
    random_lat_offset = (random.random() - 0.5) * 0.02
    random_lon_offset = (random.random() - 0.5) * 0.02

    new_latitude = latitude + random_lat_offset
    new_longitude = longitude + random_lon_offset

    return new_latitude, new_longitude
