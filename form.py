import PySimpleGUI as sg
import pandas as pd
from owlready2 import *


# Add some color to the window
sg.theme('DarkTeal9')

excel_file = 'scenarios.xlsx'
df = pd.read_excel(excel_file)


onto = get_ontology("infoiag_project_2021_group1.owl")
onto.load()
cities = onto.search(is_a=onto.City)
cities_list = []
city_to_neighbourhoods = {}
neighbourhoods_with_train_station = []
for element in cities:
    if element.name == "City": continue
    cities_list.append(element.name)
    neighbourhoods = onto.search(is_a=onto.Neighbourhood,belongsToCity=element)
    city_to_neighbourhoods[element.name] = [neigh.name for neigh in neighbourhoods]
    if element.name == "amsterdam" or element.name == "utrecht": # these have train stations (hardcoded, because i coudlnt find hasTrainStation attribute)
        neighbourhoods_with_train_station = neighbourhoods_with_train_station + [neigh.name for neigh in neighbourhoods]


layout = [
    [sg.Text('Preffered cuisine or food choices', size=(30, 1)), sg.InputText(key='cuisine_food_pref')],
    [sg.Text('Cuisine or food choices to avoid', size=(30, 1)), sg.InputText(key='cuisine_food_avoid')],


    [sg.Text('Select a restaurant price range', size=(30, 1)), sg.Combo(['Cheap', 'Moderate', 'Expensive'], key='restaurant_price_range')],
    # either the above or we make them enter their savings /salary as input text and then we determine whether we find them cheap moderate or expensive restaurants,
    # but they might want cheap restaurants even if they earn little or vice versa

    # [sg.Text('Do you want to eat out', size=(30, 1)), sg.Radio('Yes', "RADIO1", key="eat_out_yes", default=True), sg.Radio('No', "RADIO1", key="eat_out_no")],
    # # seems unnecesary, doesnt everyone?

    [sg.Text('Select the city you live in', size=(30, 1)), sg.Combo(cities_list, key='select_cities', enable_events=True)],
    [sg.Text('Select the neighbourhood you live in', size=(30, 1)), sg.Combo(['Please select a city first'], key='select_neighbourhood', enable_events=True)],


    [sg.Text('Select the modes of transport you preffer', size=(30, 1)),sg.Checkbox('Car (gas)', key="pref_transport_gas_car"), sg.Checkbox('Car (electric)',key="pref_transport_electric_car"), sg.Checkbox('Ride-share', key="pref_transport_rideshare"), sg.Checkbox('Train',key="pref_transport_train"), sg.Checkbox('Bike', key="pref_transport_bike")],

    [sg.Text('Select any health conditions you might have', size=(30, 1)), sg.Checkbox('COVID symptoms', key="condition_covid"), sg.Checkbox('Gluten allergy',key="condition_gluten"), sg.Checkbox('Lactose intolerance', key="condition_lactose")],

    [sg.Text('Select any additional prefferences', size=(30, 1)), sg.Radio('No CO2 preference', "RADIO2", default=True, key="pref_co2_none"),sg.Radio('Low CO2 food', "RADIO2",key="pref_co2_low_food"),sg.Radio('Low Co2 transport', "RADIO2", key="pref_co2_low_transport")],
    [sg.Text('', size=(30, 1)), sg.Radio('No transport preference', "RADIO3", default=True, key="pref_transport_none"), sg.Radio('Fast transport', "RADIO3",key="pref_transport_fast"), sg.Radio('Cheap transport', "RADIO3", key="pref_transport_cheap")],

    [sg.Submit(), sg.Button('Clear'), sg.Exit()]
]

window = sg.Window('Simple data entry form', layout)

def clear_input():
    for key in values:
        window[key]('')
    return None

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Exit':
        break
    if event == 'Clear':
        clear_input()
    if event == 'select_cities':
        city_name = values['select_cities']
        available_values = city_to_neighbourhoods[city_name]
        window.Element('select_neighbourhood').update(values=available_values)
    if event == 'select_neighbourhood':
        neighbourhood = values['select_neighbourhood']
        window.Element('pref_transport_train').update(disabled=False)
        if neighbourhood not in neighbourhoods_with_train_station:
            window.Element('pref_transport_train').update(value=False,disabled=True)


    if event == 'Submit':
        if values['select_neighbourhood'] == 'Please select a city first':
            sg.popup_ok('Please select a city from the dropdown menu and a valid neighbourhood')
            continue

        window.Element('select_neighbourhood').update(values=['Please select a city first'])
        window.Element('pref_co2_none').update(value=True)
        window.Element('pref_transport_none').update(value=True)
        window.Element('eat_out_yes').update(value=True)
        window.Element('pref_transport_train').update(disabled=False)


        df = df.append(values, ignore_index=True)
        df.to_excel(excel_file, index=False)
        sg.popup('Data saved!')
        clear_input()
window.close()