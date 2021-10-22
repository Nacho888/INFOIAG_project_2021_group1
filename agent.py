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
        candidate = self.get_levenshtein_distance(entity, self.label_to_ent.keys())
        if candidate is not None:
            result = {}
            for property in self.label_to_ent[candidate].get_properties():
                for value in property[self.ontology[candidate]]:
                    result[self.prop_to_label[property]] = value
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


    def get_transports(self, locations, preferencesCO2, preferencesPrice, availableTransports, healthConditions, neighbourhood):
        result = []

        # TODO: extract the transports for the given locations taking into account where the user lives and his/her preferences

        return result


    def get_restaurants(self, preferredCuisine, avoidCuisines, healthConditions):
        result = []

        restaurants = self.ontology.search(type = self.label_to_class["Restaurant"])

        preferred_restaurants = []
        for restaurant in restaurants:
            properties = self.get_entity_values(restaurant)
            cuisine = properties["hasCuisine"]
            if cuisine == preferredCuisine:
                preferred_restaurants.append(restaurant)

        if len(preferred_restaurants > 0):
            restaurants = preferred_restaurants

        for restaurant in restaurants:
            properties = self.get_entity_values(restaurant)
            if self.apply_restaurant_filters(properties, avoidCuisines, healthConditions):
                option = {f"{properties['name']}": {"cuisine": properties["hasCuisine"], "neighbourhood": properties["establishedIn"], "meals": properties["hasCuisine"]["servesMeals"]}}
                result.append(option)

        return result


    def apply_restaurant_filters(self, restaurant, avoidCuisines, healthConditions):
        check = True

        if restaurant["hasCuisine"] == avoidCuisines:
            check = False

        meals = restaurant["hasCuisine"]["servesMeals"]
        for meal in meals:
            meal_properties = self.get_entity_values(meal)
            for food in meal_properties["hasFood"]:
                food_properties = self.get_entity_values(food)
                for nutrient in food_properties["hasNutrients"]:
                    if nutrient in healthConditions:
                        check = False

        return check

    def get_restaurants_location(self, restaurants):
        result = []

        neighbourhoods = self.ontology.search(type = self.label_to_class["Neighbourhood"])

        # TODO: check properties access and comparison of names
        for restaurant in restaurants:
            key = restaurant.keys()[0]
            restaurant_neigbourhood = restaurant[key]["neighbourhood"]
            for neighbourhood in neighbourhoods:
                if restaurant_neigbourhood == neighbourhood:
                    properties_neighbourhood = self.get_entity_values(neighbourhood)
                    option = {f"{key}": {"neighbourhood": restaurant_neigbourhood, "city": properties_neighbourhood["belongsToCity"], "location": properties_neighbourhood["belongsToCity"]["locatedAt"]}}
                    result.append(option)

        return result


    def reasoning(self, scenario_number):
        df = pd.load("scenarios.xlsx")

        df = df.iloc[scenario_number]

        options = []

        restaurants = self.get_restaurants(df["PreferredCuisine"], df["AvoidCuisine"], df["HealthConditions"])
        locations = self.get_restaurants_location(restaurants)
        transports = self.get_transports(locations, df["Additional1"], df["Additional2"], df["Transport"], df["HealthConditions"], df["Neighbourhood"])

        # TODO: iterate in some way and assign all the values to the possible combinations (options) -> how to combine restaurants (their locations)
        # with the transport

        # for restaurant, meals in restaurants.items():
        #     for meal in meals:
        #         co2 = self.calculate_co2(transport, meal, location)
        #         utility = self.get_utility(transport, meal, location)

        #         option = {"transport": transport, "restaurant": restaurant,
        #             "meal": meal, "co2": co2, "utility": utility}

        #         options.append(option)

        self.generate_output(options)



agent = Agent()

# itself (we can remove this behavior) and all the subclass (I don't know why Car shows up here, maybe because of our
# current implementation of the Transport relationship that we should reduce to electricCar and gasolineCar and get rid of Car)
# print(agent.get_subclasses("Preferences"))

# for now is just an empty set because we haven't set the property values (CO2 consumption, cost and duration)
# print(agent.get_entity_values("bike"))

# print(agent.data_dict)
