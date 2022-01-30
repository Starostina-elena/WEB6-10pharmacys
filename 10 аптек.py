import sys
from io import BytesIO
import requests
from PIL import Image

from count_zoom_for_map import count_zoom_for_map


def get_input_address_coords(toponym_to_find):
    geocoder_params = {
        "apikey": geocoder_api_key,
        "geocode": toponym_to_find,
        "format": "json"}

    response = requests.get(geocoder_api_server, params=geocoder_params)

    json_response = response.json()

    toponym = json_response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]

    toponym_coordinates = toponym["Point"]["pos"]
    toponym_longitude, toponym_lattitude = toponym_coordinates.split(" ")

    lower_corner = [float(i) for i in toponym['boundedBy']['Envelope']['lowerCorner'].split()]
    upper_corner = [float(i) for i in toponym['boundedBy']['Envelope']['upperCorner'].split()]

    return [toponym_longitude, toponym_lattitude], lower_corner, upper_corner


def find_business_near(api_key, toponym_coords, type_business):
    search_params = {
        "apikey": api_key,
        "text": type_business,
        "lang": "ru_RU",
        "ll": ",".join(toponym_coords),
        "type": "biz"
    }

    response = requests.get(search_api_server, params=search_params)

    json_response = response.json()

    x_coords = []
    y_coords = []
    time_opened = dict()

    for i in range(min(10, len(json_response['features']))):
        organization = json_response["features"][i]
        org_time_opened = organization['properties']['CompanyMetaData']['Hours']['text']
        point = organization["geometry"]["coordinates"]
        org_upper_corner = organization['properties']['boundedBy'][0]
        org_lower_corner = organization['properties']['boundedBy'][1]
        org_point = "{0},{1}".format(point[0], point[1])

        x_coords.append(org_upper_corner[0])
        x_coords.append(org_lower_corner[0])
        y_coords.append(org_upper_corner[1])
        y_coords.append(org_lower_corner[1])
        time_opened[org_point] = org_time_opened

    return x_coords, y_coords, time_opened


def get_cart(pharmacy_x_coords, pharmacy_y_coords, lower_corner, upper_corner, toponym_longitude, toponym_lattitude,
             time_opened):
    width_degrees = max(pharmacy_x_coords + [lower_corner[0], upper_corner[0]]) - \
                    min(pharmacy_x_coords + [lower_corner[0], upper_corner[0]])
    height_degrees = max(pharmacy_y_coords + [lower_corner[1], upper_corner[1]]) - \
                    min(pharmacy_y_coords + [lower_corner[1], upper_corner[1]])

    delta = str(count_zoom_for_map(width_degrees, height_degrees))

    cart_center = [
        str(min(pharmacy_x_coords + [lower_corner[0], upper_corner[0]]) + width_degrees / 2),
        str(min(pharmacy_y_coords + [lower_corner[1], upper_corner[1]]) + height_degrees / 2)
    ]

    points_pharmacy = []
    for key, value in time_opened.items():
        if value and value.split()[1] == 'круглосуточно':
            points_pharmacy.append(f'{key},pmgnm')
        elif value:
            points_pharmacy.append(f'{key},pmblm')
        else:
            points_pharmacy.append(f'{key},pmgrm')

    map_params = {
        "ll": ",".join(cart_center),
        "spn": ",".join([delta, delta]),
        'pt': f'{",".join([toponym_longitude, toponym_lattitude])},pmwtm~{"~".join(points_pharmacy)}',
        "l": "map"
    }

    response = requests.get(map_api_server, params=map_params)

    Image.open(BytesIO(
        response.content)).show()


if __name__ == '__main__':
    toponym_to_find = " ".join(sys.argv[1:])

    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
    geocoder_api_key = "40d1649f-0493-4b70-98ba-98533de7710b"
    search_api_server = "https://search-maps.yandex.ru/v1/"
    search_api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"
    map_api_server = "http://static-maps.yandex.ru/1.x/"

    input_address_coords, input_address_lower_corner, input_address_upper_corner = get_input_address_coords(
        toponym_to_find)

    pharmacy_x_coords, pharmacy_y_coords, pharmacy_time_opened = \
        find_business_near(search_api_key, input_address_coords, 'аптека')

    get_cart(pharmacy_x_coords, pharmacy_y_coords, input_address_lower_corner, input_address_upper_corner,
             *input_address_coords, pharmacy_time_opened)
