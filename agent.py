from owlready2 import *
import os
import json
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


    def get_utility(self, transport, food):
        return 0.5 * self.get_transport_utility(transport) + 0.5 * self.get_food_utility(food)


    def get_transport_utility(self, transport):
        properties = self.get_entity_values(transport)
        try:
            result = 0.6 * properties["co2Footprint"] + 0.3 * properties["cost"] + 0.1 * properties["duration"]
            return result
        except KeyError:
            print("Error when processing the transport utility")
            return 0

    def get_food_utility(self, food, location):
        try:
            result = self.check_food_co2_discount(food, location)
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


agent = Agent()

# itself (we can remove this behavior) and all the subclass (I don't know why Car shows up here, maybe because of our
# current implementation of the Transport relationship that we should reduce to electricCar and gasolineCar and get rid of Car)
# print(agent.get_subclasses("Preferences"))

# for now is just an empty set because we haven't set the property values (CO2 consumption, cost and duration)
# print(agent.get_entity_values("bike"))

print(agent.data_dict)