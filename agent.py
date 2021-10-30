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
            result = 0.6 * abs(properties["co2Footprint"][0] - 100) + 0.3 * abs(properties["cost"][0] - 100) + 0.1 * abs(properties["duration"][0] - 100)
            return result
        except KeyError:
            print("Error when processing the transport utility")
            return 0


    # def change_range_value(self, value, old_min, old_max, new_min, new_max):
    #     old_range = old_max - old_min
    #     new_range = new_max - new_min
    #     return ((value - old_min) * new_range) / old_range + new_min


    def get_food_utility(self, meal, location):
        try:
            result = 0
            meal = self.get_entity_values(meal)
            for food in meal["hasFood"]:
                result += self.check_food_co2_discount(food, location)
            # return self.change_range_value(result, 0, result, 0, 100))
            return result
        except KeyError:
            print("Error when processing the food utility")
            return 0


    def check_food_co2_discount(self, food, location):
        properties_food = self.get_entity_values(food)
        properties_neighbourhood = self.get_entity_values(location[0])
        city = properties_neighbourhood["belongsToCity"][0]
        try:
            result = abs(properties_food["co2Footprint"][0] - 100)
            if properties_food["producedIn"][0] == self.get_entity_values(city)["locatedAt"]:
                result = result * 0.25
            return result
        except KeyError:
            print("Error when processing the food CO2 discount")
            return 0


    def generate_output(self, options):
        result = {}
        for i, option in enumerate(options, start=1):
            result[f"option{i}"] = {"transport": option["transport"], "restaurant": option["restaurant"],
            "meal": option["meal"], "co2": option["co2"], "utility": option["utility"]}
        sorted_tuples = sorted(result.items(), key=lambda x: x[1]["utility"])
        sorted_result = {k: v for k, v in sorted_tuples}
        with open("output.json", "w") as f:
            json.dump(sorted_result, f, indent=4)


    def calculate_co2(self, transport, meal, location):
        total_co2 = 0
        properties_transport = self.get_entity_values(transport)
        try:
            total_co2 += properties_transport["co2Footprint"][0]
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
            cuisine = self.ent_to_label[properties["hasCuisine"][0]]
            if cuisine in preferred_cuisines:
                preferred_restaurants.append(restaurant)

        if len(preferred_restaurants) > 0:
            restaurants = preferred_restaurants

        for restaurant in restaurants:
            properties = self.get_entity_values(restaurant)
            filtered = self.apply_restaurant_filters(properties, avoid_cuisines, health_conditions, preferences_CO2)
            if len(filtered) > 0:
                cuisine = self.get_entity_values(properties["hasCuisine"][0])
                option = {f"{self.ent_to_label[restaurant]}": {"cuisine": cuisine, "neighbourhood": properties["hasEstablishmentAt"], "meals": filtered}}
                result.append(option)

        return result


    def apply_restaurant_filters(self, restaurant, avoid_cuisines, health_conditions, preferences_CO2):
        ok_meals = []

        cuisine = self.get_entity_values(restaurant["hasCuisine"][0])

        if cuisine in avoid_cuisines:
            return ok_meals

        for meal in cuisine["servesMeals"]:
            meal_properties = self.get_entity_values(meal)
            check_food = True
            for food in meal_properties["hasFood"]:
                food_properties = self.get_entity_values(food)
                for nutrient in food_properties["hasNutrients"]:
                    nutrient = self.ent_to_label[nutrient]
                    if nutrient in health_conditions:
                        check_food = False
                if ("lowCO2Food" in preferences_CO2 or "lowCO2All" in preferences_CO2) and food_properties["co2Footprint"][0] > 50:
                    check_food = False
            if check_food:
                ok_meals.append(meal)

        return ok_meals


    def get_restaurants_location(self, restaurants):
        result = []

        neighbourhoods = self.ontology.search(type = self.label_to_class["Neighbourhood"])

        for restaurant in restaurants:
            key = next(iter(restaurant))
            restaurant_neigbourhood = restaurant[key]["neighbourhood"][0]
            for neighbourhood in neighbourhoods:
                if self.ent_to_label[restaurant_neigbourhood] == self.ent_to_label[neighbourhood]:
                    properties_neighbourhood = self.get_entity_values(neighbourhood)
                    city = properties_neighbourhood["belongsToCity"][0]
                    city_properties = self.get_entity_values(city)
                    option = {f"{key}": {"neighbourhood": restaurant_neigbourhood, "city": city, "location": city_properties["locatedAt"]}}
                    result.append(option)

        return result


    def process_preferences(self, has_preferences, preference_names):
        result = []
        for i, preference in enumerate(has_preferences):
            try:
                if int(preference) == 1:
                    result.append(preference_names[i])
                elif int(preference) == 0:
                    pass
            except ValueError:  # Price ranges
                result.append(preference.lower())
        return result


    def process_input_lists(self, str_list):
        return str_list.strip("[]").replace("'", "").split(",")


    def reasoning(self, scenario_number):
        df = pd.read_json("scenarios.json")

        df = df.iloc[scenario_number]

        options = []

        # Preference preprocessing
        health_conditions = self.process_preferences([df["condition_muscle_ache"], df["condition_covid"], df["condition_gluten"], df["condition_lactose"]], ["muscleAche", "covid", "gluten", "lactose"])
        transport_preferences = self.process_preferences([df["pref_transport_bike"], df["pref_transport_electric_car"], df["pref_transport_gas_car"], df["pref_transport_rideshare"], df["pref_transport_train"]], ["bike", "electricCar", "gasolineCar", "rideShare", "train"])
        preferred_cuisines = self.process_input_lists(df["cuisine_food_pref"])
        avoid_cuisines = self.process_input_lists(df["cuisine_food_avoid"])
        low_co2 = self.process_preferences([df["pref_co2_low_food"], df["pref_co2_low_food_and_transport"], df["pref_co2_low_transport"]], ["lowCO2Food", "lowCO2All", "lowCO2Transport"])
        other_preferences = self.process_preferences([df["pref_transport_fast"], df["pref_transport_cheap"], df["restaurant_price_range"]], ["fast", "cheap"])

        print("\n** EXTRACTED USER PREFERENCES **\n")
        print(f"Health conditions:\n\t{health_conditions}")
        print(f"Available transports:\n\t{transport_preferences}")
        print(f"Preferred cuisines:\n\t{preferred_cuisines}")
        print(f"Cuisines to avoid:\n\t{avoid_cuisines}")
        print(f"Low CO2 requirements:\n\t{low_co2}")
        print(f"Other preferences:\n\t{other_preferences}")

        # Preference matching
        restaurants = self.get_restaurants(preferred_cuisines, avoid_cuisines, health_conditions, low_co2)
        locations = self.get_restaurants_location(restaurants)
        available_transports, ride_shares = self.get_transports(locations, low_co2, other_preferences, transport_preferences, health_conditions, df["select_neighbourhood"])

        # Options' extraction given the results
        ride_share_counter = 0
        for transport in available_transports:
            for restaurant in restaurants:
                key = next(iter(restaurant))
                restaurant_location = restaurant[key]["neighbourhood"]
                if transport == "rideShare" and ride_shares[ride_share_counter] == restaurant_location:
                    transport = "rideShare"
                for meal in restaurant[key]["meals"]:
                    co2 = self.calculate_co2(transport, meal, restaurant_location)
                    utility = self.get_utility(transport, meal, restaurant_location)

                    option = {"transport": transport, "restaurant": key,
                        "meal": self.ent_to_label[meal], "co2": co2, "utility": utility}

                    options.append(option)

        self.generate_output(options)
        self.display_options()


    def display_options(self):
        print("\n** AGENT OUTPUT **")

        options = None
        try:
            with open("output.json", "r") as f:
                options = json.load(f)
        except json.JSONDecodeError:
            pass
        except IOError:
            pass

        if options is None:
            print(f"\nThe agent could not find a feasible combination of transport and food that complies with your preferences. Try to underconstraint a little bit your selection.")
        else:
            finished = False
            counter = 0
            get_top, more = "", ""
            while not finished:
                try:
                    option = list(options)[counter]
                except IndexError:
                    print("\nThere is no more options to display. Thanks for using the system!")
                    break
                selected_option = options[option]
                print(f"\nThe selected restaurant is {selected_option['restaurant']} where you can eat {selected_option['meal']}. You will get there by {selected_option['transport']}. This option has a total CO2 consumption of {selected_option['co2']} and an utility of {selected_option['utility']} calculated by the agent and respecting all of your preferences.")
                if counter > 0:
                    while get_top not in ["y", "n"]:
                        get_top = input("\nDo you want to see the best option again? (y/n): ")
                if get_top != "y":
                    while more not in ["y", "n"]:
                        more = input("\nDo you want to see the next option? (y/n): ")
                if get_top == "y":
                    get_top, more = "", ""
                    counter = 0
                elif more == "y":
                    get_top, more = "", ""
                    counter += 1
                else:
                    print(f"\nThanks for using the system!")
                    finished = True


agent = Agent()

agent.reasoning(1)