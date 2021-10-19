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
            return self.label_to_ent[candidate].get_properties()
        print(f"No entity named {entity} found")
        return []


agent = Agent()

# itself (we can remove this behavior) and all the subclass (I don't know why Car shows up here, maybe because of our
# current implementation of the Transport relationship that we should reduce to electricCar and gasolineCar and get rid of Car)
print(agent.get_subclasses("Preferences"))

# for now is just an empty set because we haven't set the property values (CO2 consumption, cost and duration)
print(agent.get_entity_values("bike"))