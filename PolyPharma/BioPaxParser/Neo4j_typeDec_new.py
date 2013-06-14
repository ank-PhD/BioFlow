'''
Created on Jun 13, 2013

@author: andrei
'''

from bulbs.model import Node, Relationship
from bulbs.property import String, Integer, Float, Dictionary, List
from bulbs.utils import current_datetime

s
class CostumNode(Node):             # Serves as a basis for the annotation
    element_type="CostumNode"
    ID=String(nullable=False)       # Reactome import heritage
    displayName=String()            # To see what it is, for the human operator
    custom=String()                 # Just in case
    load=Float()                    # To freeze information transmission score (Dict should be better?)

class AnnotNode(Node):                  # Used mainly the simplest annotation basis annotation
    element_type="AnnotNode"   
    ContentType=String(nullable=False)  # Payload type          
    Contents=String(nullable=False)     # Indexed payload
 
class CostumLink(Relationship):
    label="CostumLink"
    linkType=String()
    custom=String()
    load=Float()

#<====================================>
    
class Meta(CostumNode):
    element_type="Meta"
    
class Fragment(CostumNode):
    element_type="Fragment"
    locationType=String()           # SPAN or POINT
    location=String(nullable=False) # Location is protein-relative

class Instantiation_Type(CostumNode):
    element_type="Instantiation_Type"
    type=String()                   # Instantiation type: 

class Instance(CostumNode):
    element_type="Instance"
    
class Collection(CostumNode):
    element_type="Collection"

class Reaction(CostumNode):
    element_type="Reaction"
    frequency=Float()
    
#<=====================================>

class DNA(Meta):
    element_type="DNA"

class Location(Instantiation_Type):
    element_type="Location"

class Meta2Location(Instantiation_Type):
    element_type="Localizes"

class DNA_Collection(Meta):
    element_type="DNA Collection"

class Collection2Meta(CostumLink):
    label="Part_of_Collection"

class Meta2AnnotNode(Relationship):
    label="external_Reference"

class Complex(Meta):
    element_type="Complex"

class Complex2Meta(Relationship):
    element_type="Part_of_Complex"

class Complex_Collection(Meta):
    element_type="Complex_Collection"

class Catalysis(CostumLink):
    element_type="Catalysis"
    controlType=String()
    ID=String(nullable=False)
    displayName=String()
    
class Regulation(CostumLink):
    element_type="Regulation"
    controlType=String()
    ID=String(nullable=False)
    displayName=String()

class PhysicalEntity(Meta):
    element_type="PhysicalEntity"
    
class PhysicalEntity_Collection(Meta):
    element_type="PhysicalEntity_Collection"

class TemplateReaction(Reaction):
    element_type="TemplateReaction"
    
class Degradation(Reaction):
    element_type="Degradation"

class RNA(Meta):
    element_type="RNA"
    
class RNA_Collection(Meta):
    element_type="RNA_Collection"

class Originating_Organism(Instantiation_Type):
    element_type="Originating_Organism"

class Meta2OriginatingOrganism(Relationship):
    label="Belongs to an organism"
    
class Protein(Meta):    
    element_type="Protein"

class Protein__Collection(Meta):
    element_type="Protein_Collection"

class SmallMolecule(Meta):
    element_type="Small_Molecule"

class SmallMolecule_Collection(Meta):
    element_type="Small_Molecule_Collection"

class BiochemicalReaction(Reaction):
    element_type="Biochemical_Reaction"
    
class ReactionParticipant(CostumLink):
    element_type="Reaction_Particpant"
    side=String()

class ModificationFeature(Instantiation_Type):
    element_type="Modification_Feature"
    location=String()