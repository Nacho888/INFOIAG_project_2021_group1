import PySimpleGUI as sg
import pandas as pd

# Add some color to the window
sg.theme('DarkTeal9')

excel_file = 'scenarios.xlsx'
df = pd.read_excel(excel_file)

layout = [
    [sg.Text('Preffered cuisine or food choices', size=(30, 1)), sg.InputText(key='Enter preffered cuisines or foods')],
    [sg.Text('Cuisine or food choices to avoid', size=(30, 1)), sg.InputText(key='Enter cuisines or foods to avoid')],


    [sg.Text('Select a restaurant price range', size=(30, 1)), sg.Combo(['Cheap', 'Moderate', 'Expensive'], key='Restaurant price range')],
    # either the above or we make them enter their savings /salary as input text and then we determine whether we find them cheap moderate or expensive restaurants,
    # but they might want cheap restaurants even if they earn little or vice versa

    [sg.Text('Do you want to eat out', size=(30, 1)), sg.Radio('Yes', "RADIO1", default=True),sg.Radio('No', "RADIO1")],
    # seems unnecesary, doesnt everyone?

    [sg.Text('Select the city you live in', size=(30, 1)), sg.Combo(['City 1', 'City 2', 'City 3', 'City 4', 'City 5', 'City 6', 'City 7'], key='')],
    [sg.Text('Select the neighbourhood you live in', size=(30, 1)), sg.Combo(['Neighbourhood from selected city 1', 'Neighbourhood from selected city 2', 'Neighbourhood from selected city 3'], key='')],
    # TODO: need to add logic so that based on the selected city we find neighbourhoods inside it and present those as options

    [sg.Text('Select the modes of transport you preffer', size=(30, 1)),sg.Checkbox('Car (gas)'),sg.Checkbox('Car (electric)'), sg.Checkbox('Ride-share'), sg.Checkbox('Train'), sg.Checkbox('Bike')],
    # preffered transportation, TODO: if neighbourhood doesnt include train station, train should be disabled

    [sg.Text('Select any health conditions you might have', size=(30, 1)), sg.Checkbox('COVID symptoms'),sg.Checkbox('Gluten allergy'), sg.Checkbox('Lactose intolerance')],

    [sg.Text('Select any additional prefferences', size=(30, 1)),sg.Radio('None', "RADIO2", default=True),sg.Radio('Low Co2 food', "RADIO2"),sg.Radio('Low Co2 transport', "RADIO2")],
    [sg.Text('Select any additional prefferences', size=(30, 1)), sg.Radio('None', "RADIO3", default=True),sg.Radio('Fast transport', "RADIO3"), sg.Radio('Cheap transport', "RADIO3")],

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
    if event == 'Submit':
        df = df.append(values, ignore_index=True)
        df.to_excel(excel_file, index=False)
        sg.popup('Data saved!')
        clear_input()
window.close()