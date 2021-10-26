from owlready2 import *
import os
import json
import pandas as pd
from Levenshtein import distance

class Agent:

    def __init__(self, path="infoiag_project_2021_group1.owl"):
        # Load the desired ontology using the path file
        self.ontology = get_ontology(path).load()

        # Run the reasoner to obtain the inferences
        try:
            owlready2.JAVA_EXE = os.getenv('JAVA_HOME') + "/bin/java.exe"
            with self.ontology:
                sync_reasoner(infer_property_values=True)
        except FileNotFoundError:
            print("Make sure that you have Java installed and defined in your environment path variables.")

        # Mappings between names (str) and OWL
        self.label_to_class = {ent._name: ent for ent in self.ontology.classes()}  # "COVID": infoiag_project_2021_group1.COVID
        self.label_to_prop = {prop._name: prop for prop in self.ontology.properties()}  #  "co2Footprint": infoiag_project_2021_group1.co2Footprint
        self.label_to_ent = {individual._name: individual for individual in self.ontology.individuals()}  # "bike": infoiag_project_2021_group1.bike

        self.class_to_label = {ent:ent._name for ent in self.ontology.classes()} # infoiag_project_2021_group1.COVID: "COVID"
        self.prop_to_label = {prop:prop._name for prop in self.ontology.properties()} #  infoiag_project_2021_group1.co2Footprint: "co2Footprint"
        self.ent_to_label = {individual:individual._name for individual in self.ontology.individuals()}  # infoiag_project_2021_group1.bike: "bike"

        # All the data in OWL representation
        self.data_dict = {"classes": list(self.ontology.classes()), "data_properties": list(self.ontology.data_properties()), "object_properties": list(self.ontology.object_properties()), "entities": list(self.ontology.individuals())}


    def get_levenshtein_distance(self, word, possible_values):
        threshold = 3
        min_distance = 999
        candidate = None
        for value in possible_values:
            dist = distance(word, value)
            if dist < threshold and dist < min_distance:
                min_distance = dist
                candidate = value
        return candidate


    def get_subclasses(self, parent):
        candidate = self.get_levenshtein_distance(parent, self.label_to_class.keys())
        if candidate is not None:
            return self.ontology.search(subclass_of = self.label_to_class[candidate])
        print(f"No concept named {parent} found")
        return []


    def get_entity_values(self, entity):
        if type(entity) != str:
            entity = self.ent_to_label[entity]
        candidate = self.get_levenshtein_distance(entity, self.label_to_ent.keys())
        if candidate is not None:
            result = {}
            for property in self.label_to_ent[candidate].get_properties():
                result[self.prop_to_label[property]] = property[self.ontology[candidate]]
            return result
        print(f"No entity named {entity} found")
        return {}


    def get_utility(self, transport, meal, location):
        return 0.5 * self.get_transport_utility(transport) + 0.5 * self.get_food_utility(meal, location)


    def get_transport_utility(self, transport):
        properties = self.get_entity_values(transport)
        try:
            result = 0.6 * properties["co2Footprint"] + 0.3 * properties["cost"] + 0.1 * properties["duration"]
            return result
        except KeyError:
            print("Error when processing the transport utility")
            return 0


    def get_food_utility(self, meal, location):
        try:
            result = 0
            meal = self.get_entity_values(meal)
            for food in meal["foods"]:
                result += self.check_food_co2_discount(food, location)
            return result
        except KeyError:
            print("Error when processing the food utility")
            return 0


    def check_food_co2_discount(self, food, location):
        properties_food = self.get_entity_values(food)
        location = self.ent_to_label[location]
        try:
            result = properties_food["co2Footprint"]
            if properties_food["producedIn"] == location:
                result = result * 0.25
        except KeyError:
            print("Error when processing the food CO2 discount")
            return 0


    def generate_output(self, options):
        result = {}
        for i, option in enumerate(options, start=1):
            result[f"option{i}"] = {"transport": option["transport"], "restaurant": option["restaurant"],
            "meal": option["meal"], "co2": option["co2"], "utility": option["utility"]}
        sorted_tuples = sorted(result.items(), key=lambda x: x["utility"])
        sorted_result = {k: v for k, v in sorted_tuples}
        json.dumps(sorted_result, indent=4)


    def calculate_co2(self, transport, meal, location):
        total_co2 = 0
        properties_transport = self.get_entity_values(transport)
        try:
            total_co2 += properties_transport["co2Footprint"]
            total_co2 += self.get_food_utility(meal, location)
            return total_co2
        except KeyError:
            print("Error when processing the total CO2 consumption")
            return 0


    def get_transports(self, locations, preferences_CO2, other_preferences, available_transports, health_conditions, neighbourhood):
        # I know that this could be cleaner... It's just a quick sketch, if someone wants to change atm, go for it ;)

        if "covid" in health_conditions:
            try:
                available_transports.remove("train")
            except ValueError:
                pass

        if "fast" in other_preferences or "muscleAche" in health_conditions:
            try:
                available_transports.remove("walking")
            except ValueError:
                pass
            try:
                available_transports.remove("bike")
            except ValueError:
                pass

        if "cheap" in other_preferences:
            try:
                available_transports.remove("electricCar")
            except ValueError:
                pass
            try:
                available_transports.remove("gasolineCar")
            except ValueError:
                pass
            try:
                available_transports.remove("rideShare")
            except ValueError:
                pass

        if "moderate" in other_preferences:
            try:
                available_transports.remove("electricCar")
            except ValueError:
                pass
            try:
                available_transports.remove("gasolineCar")
            except ValueError:
                pass

        if "lowCO2Transport" in preferences_CO2 or "lowCO2All" in preferences_CO2:
            try:
                available_transports.remove("gasolineCar")
            except ValueError:
                pass

        rideShares = []
        for location in locations:
            if location == neighbourhood and "rideShare" in available_transports:
                rideShares.append(neighbourhood)

        return available_transports, rideShares


    def get_restaurants(self, preferred_cuisines, avoid_cuisines, health_conditions, preferences_CO2):
        result = []

        restaurants = self.ontology.search(type = self.label_to_class["Restaurant"])

        preferred_restaurants = []
        for restaurant in restaurants:
            properties = self.get_entity_values(restaurant)
            cuisine = properties["hasCuisine"]
            if cuisine in preferred_cuisines:
                preferred_restaurants.append(restaurant)

        if len(preferred_restaurants > 0):
            restaurants = preferred_restaurants

        for restaurant in restaurants:
            properties = self.get_entity_values(restaurant)
            filtered = self.apply_restaurant_filters(properties, avoid_cuisines, health_conditions, preferences_CO2)
            if len(filtered) > 0:
                cuisine = self.get_entity_values(properties["hasCuisine"])
                option = {f"{properties['name']}": {"cuisine": cuisine, "neighbourhood": properties["establishedIn"], "meals": filtered}}
                result.append(option)

        return result


    def apply_restaurant_filters(self, restaurant, avoid_cuisines, health_conditions, preferences_CO2):
        ok_meals = []

        cuisine = self.get_entity_values(restaurant["hasCuisine"])

        if cuisine in avoid_cuisines:
            return ok_meals

        meals = self.get_entity_values(cuisine["servesMeals"])
        for meal in meals:
            meal_properties = self.get_entity_values(meal)
            for food in self.get_entity_values(meal_properties["hasFood"]):
                food_properties = self.get_entity_values(food)
                check_food = True
                for nutrient in self.get_entity_values(food_properties["hasNutrients"]):
                    if nutrient in health_conditions:
                        check_food = False
                if ("lowCO2Food" in preferences_CO2 or "lowCO2All" in preferences_CO2) and food_properties["co2Footprint"] > 50:
                    check_food = False
                if check_food:
                    ok_meals.append(meal)

        return ok_meals


    def get_restaurants_location(self, restaurants):
        result = []

        neighbourhoods = self.ontology.search(type = self.label_to_class["Neighbourhood"])

        for restaurant in restaurants:
            key = restaurant.keys()[0]
            restaurant_neigbourhood = restaurant[key]["neighbourhood"]
            for neighbourhood in neighbourhoods:
                print(f"Comparing neighbourhood: {neighbourhood} to restaurant neighbourhood: {restaurant_neigbourhood}")
                if restaurant_neigbourhood == neighbourhood:
                    print("Equal")
                    properties_neighbourhood = self.get_entity_values(neighbourhood)
                    city = properties_neighbourhood["belongsToCity"]
                    city_properties = self.get_entity_values(city)
                    option = {f"{key}": {"neighbourhood": restaurant_neigbourhood, "city": city, "location": city_properties["locatedAt"]}}
                    result.append(option)

        return result


    def process_preferences(self, has_preferences, preference_names):
        result = []
        for i, preference in enumerate(has_preferences):
            if int(preference) == 1:
                result.apppend(preference_names[i])
            elif int(preference) == 0:
                pass
            else:  # Price ranges
                result.append(preference.lower())
        return result


    def process_input_lists(str_list):
        return str_list.strip("[]").replace("'", "").split(",")


    def reasoning(self, scenario_number):
        df = pd.load("scenarios.xlsx")

        df = df.iloc[scenario_number]

        options = []

        # Preference preprocessing
        health_conditions = self.process_preferences([df["condition_muscle_ache"], df["condition_covid"], df["condition_gluten"], df["condition_lactose"]], ["muscleAche", "covid", "gluten", "lactose"])
        transport_preferences = self.process_preferences(df["pref_transport_bike"], df["pref_transport_electric_car"], df["pref_transport_gas_car"], df["pref_transport_rideshare"], df["pref_transport_train"], ["bike", "electricCar", "gasolineCar", "rideShare", "train"])
        preferred_cuisines = self.process_input_lists(df["cuisine_food_pref"])
        avoid_cuisines = self.process_input_lists(df["cuisine_food_avoid"])
        low_co2 = self.process_preferences([df["pref_co2_low_food"], df["pref_co2_low_food_and_transport"], df["pref_co2_low_transport"]], ["lowCO2Food", "lowCO2All", "lowCO2Transport"])
        other_preferences = self.process_preferences([df["pref_transport_fast"], df["restaurant_price_range"]], ["fast"])

        # Preference matching
        restaurants = self.get_restaurants(preferred_cuisines, avoid_cuisines, health_conditions, low_co2)
        locations = self.get_restaurants_location(restaurants)
        available_transports, ride_shares = self.get_transports(locations, low_co2, other_preferences, transport_preferences, health_conditions, df["select_neighbourhood"])

        # Options' extraction given the results
        ride_share_counter = 0
        for restaurant, meals in restaurants.items():
            restaurant_location = self.get_entity_values(restaurant)["establishedIn"]
            for transport in available_transports:
                if transport == "rideShare" and ride_shares[ride_share_counter] == restaurant_location:
                    transport = "rideShare"
                for meal in meals:
                    co2 = self.calculate_co2(transport, meal, restaurant_location)
                    utility = self.get_utility(transport, meal, restaurant_location)

                    option = {"transport": transport, "restaurant": restaurant,
                        "meal": meal, "co2": co2, "utility": utility}

                    options.append(option)

        self.generate_output(options)
        self.display_options()


    def display_options(self):
        options = json.loads("output.json")
        output_str = ""

        if not options:
            output_str += f"The agent could not find a feasible combination of transport and food that complies with your preferences. Try to underconstraint a little bit your selection."
        else:
            finished = False
            counter = 0
            get_top, more = ""
            while not finished:
                option = options[counter]
                selected_option = options[option]
                output_str += f"The selected restaurant is {selected_option['restaurant']} where you can eat {selected_option['meal']}. You will get there by {selected_option['transport']}. This option has a total CO2 consumption of {selected_option['co2']} and an utility of {selected_option['utility']} calculated by the agent and respecting all of your preferences"
                print(output_str + "\n")
                if counter > 0:
                    while get_top != "y" or more != "n":
                        get_top = input("Do you want to see the best option again? (y/n): ")
                        counter = 0
                if get_top != "y":
                    while more != "y" or more != "n":
                        more = input("Do you want to see the next option? (y/n): ")
                    if more == "y":
                        counter += 1
                    else:
                        finished = True

agent = Agent()

# print(agent.data_dict)
