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
        except (FileNotFoundError, TypeError):
            print("Make sure that you have Java installed and defined in your environment path variables (jdk folder).")

        # Mappings between names (str) and OWL
        self.label_to_class = {ent._name: ent for ent in self.ontology.classes()}  # "COVID": infoiag_project_2021_group1.COVID
        self.label_to_prop = {prop._name: prop for prop in self.ontology.properties()}  #  "co2Footprint": infoiag_project_2021_group1.co2Footprint
        self.label_to_ent = {individual._name: individual for individual in self.ontology.individuals()}  # "bike": infoiag_project_2021_group1.bike

        self.class_to_label = {ent:ent._name for ent in self.ontology.classes()} # infoiag_project_2021_group1.COVID: "COVID"
        self.prop_to_label = {prop:prop._name for prop in self.ontology.properties()} #  infoiag_project_2021_group1.co2Footprint: "co2Footprint"
        self.ent_to_label = {individual:individual._name for individual in self.ontology.individuals()}  # infoiag_project_2021_group1.bike: "bike"

        # All the data in OWL representation
        self.data_dict = {"classes": list(self.ontology.classes()),
        "data_properties": list(self.ontology.data_properties()),
        "object_properties": list(self.ontology.object_properties()),
        "entities": list(self.ontology.individuals())}

        self.weights = { # default values
            "MAIN_FOOD": 0.5,
            "MAIN_TRANSPORT": 0.5,
            "TRANSPORT_CO2": 0.6,
            "TRANSPORT_COST": 0.3,
            "TRANSPORT_DURATION": 0.1,
        }

    def set_weights(self, co2, other_preferences, restaurant_crowdedness):
        # just a crude heuristic so we can kind of estimate how much the user cares about his food versus his transport, so this is reflected in the utility function weights
        food_points = 1
        t_co2_points = 1
        t_cost_points = 1
        t_duration_points = 1
        if co2[0] == 'lowCO2Transport': t_co2_points += 10
        if co2[0] == 'lowCO2All':
            t_co2_points += 10
            food_points += 10
        if co2[0] == 'lowCO2Food': food_points += 10

        if other_preferences[0] =='fast': t_duration_points += 10
        if other_preferences[0] =='cheap': t_cost_points += 10

        if other_preferences[1] =='moderate': food_points += 15
        if other_preferences[1] =='cheap': food_points += 10
        if other_preferences[1] == 'expensive': food_points += 20

        if restaurant_crowdedness[0] == 'low': food_points += 10
        if restaurant_crowdedness[0] == 'high': food_points += 10

        self.weights = {
            "MAIN_FOOD": food_points / (food_points + t_co2_points + t_cost_points + t_duration_points),
            "MAIN_TRANSPORT": (t_co2_points + t_cost_points + t_duration_points) / (food_points + t_co2_points + t_cost_points + t_duration_points),
            "TRANSPORT_CO2": t_co2_points / (t_co2_points + t_cost_points + t_duration_points),
            "TRANSPORT_COST": t_cost_points / (t_co2_points + t_cost_points + t_duration_points),
            "TRANSPORT_DURATION": t_duration_points / (t_co2_points + t_cost_points + t_duration_points),
        }

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


    def get_utility(self, transport, meal, restaurant_neighbourhood, user_neighbourhood):
        return round(abs((self.weights["MAIN_TRANSPORT"] * self.get_transport_utility(transport, restaurant_neighbourhood, user_neighbourhood) + \
        self.weights["MAIN_FOOD"] * self.get_food_utility(meal, restaurant_neighbourhood, normalized=True)) - 100), 2)


    def get_transport_utility(self, transport, restaurant_neighbourhood, user_neighbourhood):
        properties = self.get_entity_values(transport)
        try:
            result = self.weights["TRANSPORT_CO2"] * abs(properties["co2Footprint"][0] - 100) + \
            self.weights["TRANSPORT_COST"] * abs(properties["cost"][0] - 100) + \
            self.weights["TRANSPORT_DURATION"] * self.get_duration(restaurant_neighbourhood, user_neighbourhood)  # abs(properties["duration"][0] - 100)
            return result
        except KeyError:
            print("Error when processing the transport utility")
            return 0


    def get_duration(self, restaurant_neighbourhood, user_neighbourhood):
        duration = 0
        cost_travel_neighbourhood = 10
        cost_travel_city = 80

        properties_restaurant_neighbourhood = self.get_entity_values(restaurant_neighbourhood[0])
        properties_user_neighbourhood = self.get_entity_values(user_neighbourhood)

        city_restaurant = self.ent_to_label[properties_restaurant_neighbourhood["belongsToCity"][0]]
        city_user = self.ent_to_label[properties_user_neighbourhood["belongsToCity"][0]]

        if city_restaurant == city_user:
            adjacents = [self.ent_to_label[x] for x in properties_restaurant_neighbourhood["adjacentTo"]]
            if user_neighbourhood in adjacents:
                duration += cost_travel_neighbourhood
            elif user_neighbourhood == restaurant_neighbourhood[0]:
                pass
            else:
                while user_neighbourhood not in adjacents:
                    duration += cost_travel_neighbourhood
                    updated_adjacents = []
                    for neigh in adjacents:
                        properties_neigh = self.get_entity_values(neigh)
                        for adj_neigh in properties_neigh["adjacentTo"]:
                            updated_adjacents.append(adj_neigh)
                    adjacents = [self.ent_to_label[x] for x in updated_adjacents]
                    if len(adjacents) == 0: break
        else:
            duration += cost_travel_city

        return duration


    def get_food_utility(self, meal, neighbourhood, normalized=False):
        try:
            result = 0
            meal = self.get_entity_values(meal)
            for food in meal["hasFood"]:
                result += self.check_food_co2_discount(food, neighbourhood)
            if normalized: return result / len(meal["hasFood"])
            return result
        except KeyError:
            print("Error when processing the food utility")
            return 0


    def check_food_co2_discount(self, food, neighbourhood):
        properties_food = self.get_entity_values(food)
        properties_neighbourhood = self.get_entity_values(neighbourhood[0])
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
        sorted_tuples = sorted(result.items(), key=lambda x: x[1]["utility"], reverse=True)
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
        if "covid" in health_conditions and "train" in available_transports:
            available_transports.remove("train")

        if "fast" in other_preferences or "muscleAche" in health_conditions:
            if "walking" in available_transports:
                available_transports.remove("walking")
            if "bike" in available_transports:
                available_transports.remove("bike")

        if "cheap" in other_preferences:
            if "electricCar" in available_transports:
                available_transports.remove("electricCar")
            if "gasolineCar" in available_transports:
                available_transports.remove("gasolineCar")
            if "rideShare" in available_transports:
                available_transports.remove("rideShare")

        if "moderate" in other_preferences:
            if "electricCar" in available_transports:
                available_transports.remove("electricCar")
            if "gasolineCar" in available_transports:
                available_transports.remove("gasolineCar")

        if "lowCO2Transport" in preferences_CO2 or "lowCO2All" in preferences_CO2:
            if "gasolineCar" in available_transports:
                available_transports.remove("gasolineCar")

        rideShares = []
        for location in locations:
            if location == neighbourhood and "rideShare" in available_transports:
                rideShares.append(neighbourhood)

        return available_transports, rideShares


    def get_restaurants(self, preferred_cuisines, avoid_cuisines, health_conditions, preferences_CO2, restaurant_crowdedness):
        result = []

        restaurants = self.ontology.search(type = self.label_to_class["Restaurant"])

        restaurants_price_high_to_low = []
        restaurants_sort = restaurants
        while len(restaurants_sort) > 0: # dont judge me please, we have all sinned
            current_restaurant = restaurants_sort[0]
            while len(current_restaurant.isCheaperThan) > 0 and current_restaurant.isCheaperThan[0] not in restaurants_price_high_to_low:
                current_restaurant = current_restaurant.isCheaperThan[0]
            restaurants_price_high_to_low.append(current_restaurant)
            if len(restaurants_price_high_to_low) == len(restaurants): break

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
            filtered = self.apply_restaurant_filters(properties, avoid_cuisines, health_conditions, preferences_CO2, restaurant_crowdedness)
            if len(filtered) > 0:
                cuisine = self.get_entity_values(properties["hasCuisine"][0])
                option = {f"{self.ent_to_label[restaurant]}": {"cuisine": cuisine, "neighbourhood": properties["hasEstablishmentAt"], "meals": filtered}}
                result.append(option)

        return result


    def apply_restaurant_filters(self, restaurant, avoid_cuisines, health_conditions, preferences_CO2, restaurant_crowdedness):
        ok_meals = []

        cuisine = self.get_entity_values(restaurant["hasCuisine"][0])
        crowdedness = self.get_entity_values(restaurant["hasCrowdedness"][0])

        if restaurant_crowdedness != "none":
            if restaurant_crowdedness == "low" and crowdedness == "highCrowdedness":
                return ok_meals
            elif restaurant_crowdedness == "high" and crowdedness == "lowCrowdedness":
                return ok_meals

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
        if isinstance(str_list, list): return str_list
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
        restaurant_crowdedness = self.process_preferences([df["pref_crowdedness_none"], df["pref_crowdedness_low"], df["pref_crowdedness_high"]], ["none", "low", "high"])

        print("\n** EXTRACTED USER PREFERENCES **\n")
        print(f"Health conditions:\n\t{health_conditions}")
        print(f"Available transports:\n\t{transport_preferences}")
        print(f"Preferred cuisines:\n\t{preferred_cuisines}")
        print(f"Cuisines to avoid:\n\t{avoid_cuisines}")
        print(f"Low CO2 requirements:\n\t{low_co2}")
        print(f"Crowdedness preferences:\n\t{restaurant_crowdedness}")
        print(f"Other preferences:\n\t{other_preferences}")

        self.set_weights(low_co2,other_preferences,restaurant_crowdedness)

        # Preference matching
        restaurants = self.get_restaurants(preferred_cuisines, avoid_cuisines, health_conditions, low_co2, restaurant_crowdedness)
        locations = self.get_restaurants_location(restaurants)
        available_transports, ride_shares = self.get_transports(locations, low_co2, other_preferences, transport_preferences, health_conditions, df["select_neighbourhood"])

        # Options' extraction given the results
        ride_share_counter = 0
        for transport in available_transports:
            for restaurant in restaurants:
                key = next(iter(restaurant))
                restaurant_neighbourhood = restaurant[key]["neighbourhood"]
                if transport == "rideShare" and len(ride_shares) > 0 and ride_shares[ride_share_counter] == restaurant_neighbourhood:
                    transport = "rideShare"
                for meal in restaurant[key]["meals"]:
                    co2 = self.calculate_co2(transport, meal, restaurant_neighbourhood)
                    utility = self.get_utility(transport, meal, restaurant_neighbourhood, df["select_neighbourhood"])

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