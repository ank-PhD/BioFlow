__author__ = 'ank'
"""
Contains all the tools necessary to map GO ontology and Pathway classification from the database to an Adjacency and
Laplacian graph.
"""

from PolyPharma.neo4j_Declarations.Graph_Declarator import DatabaseGraph
import copy
from time import time
import pickle
import operator
from random import shuffle
import math
from scipy.stats.kde import  gaussian_kde
import numpy as np
from pylab import plot, hist, show
from pprint import PrettyPrinter
from scipy.sparse import csr_matrix
from collections import defaultdict
from itertools import chain
from PolyPharma.neo4j_analyzer.Matrix_Interactome_DB_interface import MatrixGetter
from PolyPharma.configs import Dumps
from PolyPharma.neo4j_analyzer.knowledge_access import acceleratedInsert
from PolyPharma.neo4j_analyzer.IO_Routines import dump_object, write_to_csv, undump_object

# Creates an instance of MatrixGetter and loads pre-computed values
MG = MatrixGetter(True, False)
MG.fast_load()


# TODO: switch to the usage of Uniprot set that is independent from the Matrix_Getter, but instead is supplide by the user
    # MG.Uniprot is just an option, even though a very importatn one

# specify the relations that lead to a more general or to an equally regulated node.
GOUpTypes = ["is_a_go", "is_part_of_go"]
GORegTypes = ["is_Regulant"]


ppritner = PrettyPrinter(indent = 4)

def _characterise(objekt):
    print 'Object of size %s and type %s' %(len(objekt),type(objekt))

def _characterise_mat(matrix):
    print 'Matrix of shape %s, type %s and has %s non-zero terms' %(matrix.shape, type(matrix), len(matrix.nonzero()[0]))



class GO_Interface(object):
    """
    General calss to recover all the informations associated with GO from database and buffer them for further use.
    """

    def __init__(self, Filter, Uniprot_Node_IDs):
        self.Filtr = Filter
        self.InitSet = Uniprot_Node_IDs
        self.init_time = time()

        self.UP2GO_Dict = {}
        self.GO2UP = defaultdict(list)
        self.SeedSet = set()
        self.All_GOs = []
        self.GO2Num = {}
        self.Num2GO = {}

        self.Reachable_nodes_dict = {}
        self.Rev_Reachable_nodes_dict = {}
        self.GO_Names = {}
        self.GO_Legacy_IDs = {}
        self.rev_GO_IDs = {}

        self.Adjacency_matrix = np.zeros((2, 2))
        self.dir_adj_matrix = np.zeros((2, 2))
        self.Laplacian_matrix = np.zeros((2, 2))
        self.Weighted_Laplacian_matrix = np.zeros((2, 2))
        self.Sign_retaining_matrix = np.zeros((2, 2))

        self.TimesReached = {}
        self.accelerationDict = {}
        self.Reverse_Dict = {}
        self.GO_Node_ID2Reach = {}


    def time(self):
        """
        Times the execution

        :return: tuple containing the time since the creation of the Matrix_getter object and since the last cal of function formatted as string
        :rtype: str
        """
        it, pt = (round(time() - self.init_time), round(time() - self.partial_time))
        pload = 'total: %s m %s s, \t partial: %s m %s s' % (int(it) / 60, it % 60, int(pt) / 60, pt % 60)
        self.partial_time = time()
        return pload


    def dump_statics(self):
        dump_object(Dumps.GO_builder_stat, (self.Filtr, self.InitSet))


    def undump_statics(self):
        return undump_object(Dumps.GO_builder_stat)


    def dump_core(self):
        dump_object(Dumps.GO_dump, (self.UP2GO_Dict, self.SeedSet, self.Reachable_nodes_dict, self.GO_Names,
                                    self.GO_Legacy_IDs, self.rev_GO_IDs, self.All_GOs, self.GO2Num, self.Num2GO))


    def undump_core(self):
        self.UP2GO_Dict, self.SeedSet, self.Reachable_nodes_dict, self.GO_Names, self.GO_Legacy_IDs,\
        self.rev_GO_IDs, self.All_GOs, self.GO2Num, self.Num2GO = undump_object(Dumps.GO_dump)


    def dump_matrices(self):
        dump_object(Dumps.GO_Mats, (self.Adjacency_matrix, self.dir_adj_matrix, self.Laplacian_matrix))


    def undump_matrices(self):
        self.Adjacency_matrix, self.dir_adj_matrix, self.Laplacian_matrix = undump_object(Dumps.GO_Mats)


    def store(self):
        self.dump_statics()
        self.dump_core()
        self.dump_matrices()


    def rebuild(self):
        self.get_GO_access()
        self.get_GO_structure()
        self.get_matrixes()


    def load(self):
        """
        Preloads itself from the saved dumps, in case the Filtering system is the same

        """
        Filtr, Initset = self.undump_statics()
        if self.Filtr != Filtr:
            raise Exception("Wrong Filtering attempted to be recovered from storage")
        if self.InitSet != Initset:
            raise Exception("Wrong Initset attempted to be recovered from storage")

        self.undump_core()
        self.undump_matrices()

    def get_GO_access(self):
        """
        Loads all of the relations between the UNIPROTs and GOs as one giant dictionary

        """
        UPs_without_GO = 0
        for UP_DB_ID in self.InitSet:
            UP_Specific_GOs = []
            Root = DatabaseGraph.UNIPORT.get(UP_DB_ID)
            Node_gen = Root.bothV("is_go_annotation")
            if Node_gen:
                for GO in Node_gen:
                    if GO.Namespace in self.Filtr:
                        GOID = str(GO).split('/')[-1][:-1]
                        UP_Specific_GOs.append(GOID)
                        self.GO2UP[GOID].append(UP_DB_ID)
                        self.SeedSet.add(GOID)
            if UP_Specific_GOs == []:
                UPs_without_GO += 1
                print "Warning: UP without GO has been found. Database UP_DB_ID: %s, \t name: %s!!!!!!" % (UP_DB_ID, MG.ID2displayName[UP_DB_ID])
            else:
                self.UP2GO_Dict[UP_DB_ID] = copy.copy(UP_Specific_GOs)

        print 'total number of UPs without a GO annotation: %s out of %s' % (UPs_without_GO, len(self.InitSet))


    def get_GO_structure(self):
        """
        Loads all of the relations between the GOs that are generalisation of the seedList GOs and that are withing the types specified in Filtr

        """
        VisitedSet = set()
        seedList = copy.copy(list(self.SeedSet))
        while seedList:
            ID = seedList.pop()
            VisitedSet.add(ID)
            Local_UpList = []
            Local_Regulation_List = []
            Local_InReg_List = []
            Local_DownList = []
            GONode = DatabaseGraph.GOTerm.get(ID)
            self.GO_Names[ID] = str(GONode.displayName)
            self.GO_Legacy_IDs[ID] = str(GONode.ID)
            self.rev_GO_IDs[str(GONode.ID)] = ID
            for Typ in chain(GOUpTypes, GORegTypes):
                generator = GONode.outV(Typ)
                if not generator:
                    continue  # skip in case GO Node has no outgoing relations to other GO nodes
                for elt in generator:
                    if not elt.Namespace in self.Filtr:
                        continue  # skip in case other GO nodes are of bad type (normally skopes are well-separated, but who knows)
                    subID = str(elt).split('/')[-1][:-1]
                    if subID not in VisitedSet:
                        seedList.append(subID)
                    if Typ in GOUpTypes:
                        Local_UpList.append(subID)
                    else:
                        Local_Regulation_List.append(subID)
                rev_generator = GONode.inV(Typ)
                if not rev_generator:
                    continue
                for elt in rev_generator:
                    if not elt.Namespace in self.Filtr:
                        continue
                    subID = str(elt).split('/')[-1][:-1]
                    if Typ in GOUpTypes:
                        Local_DownList.append(subID)
                    else:
                        Local_InReg_List.append(subID)
            self.Reachable_nodes_dict[ID] = (list(set(Local_UpList)), list(set(Local_Regulation_List)), list(set(Local_DownList)), list(set(Local_InReg_List)))

        self.All_GOs = list(VisitedSet)
        self.Num2GO = dict( (i, val) for i, val in enumerate(self.All_GOs) )
        self.GO2Num = dict( (val, i) for i, val in enumerate(self.All_GOs) )



    def get_matrixes(self, include_reg = True):
        """
        Builds Undirected and directed adjacency matrices for the GO set and

        :param include_reg: if True, the regulation set is included into the matrix
        :warning: if the parameter above is set to False, get_GO_reach module will be unable to function.
        """

        def build_adjacency():
            """
            Builds undirected adjacency matrix for the GO transitions

            """
            baseMatrix = csr_matrix((len(self.All_GOs), len(self.All_GOs)))
            for node, package in self.Reachable_nodes_dict.iteritems():
                fw_nodes = package[0]
                if include_reg:
                    fw_nodes += package[1]
                for node2 in fw_nodes:
                    idx = (self.GO2Num[node], self.GO2Num[node2])
                    baseMatrix[idx] = 1
                    idx = (idx[1], idx[0])
                    baseMatrix[idx] = 1

            _characterise_mat(baseMatrix)
            self.Adjacency_matrix = copy.copy(baseMatrix)



        def build_dir_adj():
            """
            Builds directed adjacency matrix for the GO transitions

            """
            baseMatrix = csr_matrix((len(self.All_GOs), len(self.All_GOs)))
            for node, package in self.Reachable_nodes_dict.iteritems():
                fw_nodes = package[0]
                if include_reg:
                    fw_nodes += package[1]
                for node2 in fw_nodes:
                    idx = (self.GO2Num[node], self.GO2Num[node2])
                    baseMatrix[idx] = 1

                _characterise_mat(baseMatrix)
                self.dir_adj_matrix = copy.copy(baseMatrix)

        build_adjacency()
        build_dir_adj()



    def get_GO_Reach(self):
        """
        introduce the iformation computation with regulation,. Outiline: transmit to each higher-level node the
                number of nodes attainable from each node. I.e. instead of an exploration rooted at each node, use
                a simultaneous exploration of a whole tree.

        """
        Fw_Structure = dict((key, val[0] + val[1]) for key, val in self.Reachable_nodes_dict.iteritems())
        Fw_Structure_noreg = dict((key, val[0]) for key, val in self.Reachable_nodes_dict.iteritems())
        Rv_Structure = dict((key, val[2] + val[3]) for key, val in self.Reachable_nodes_dict.iteritems())
        Rv_Structure_noreg = dict((key, val[2]) for key, val in self.Reachable_nodes_dict.iteritems())
        Reach = dict((el, []) for el in self.Reachable_nodes_dict.keys())
        Leaves = set(ID for ID in Rv_Structure if not Rv_Structure[ID])
        Processed = set()

        _characterise(Leaves)


        def collapse_leaf(Node):
            """
            Collapses all the leaves pointing to a particular Node

            Also calls and modifies parameter from the external scope:
                * Structure: dict of Forwards links, ie. NodeId 2 Up or Regulating Nodes
                * Structure: dict of Reverse links, ie. NodeId 2 Down or Regulated_by Nodes
                * Stores processed results: structure storing the Nodes that were leafs but were collapsed


            :param Node: Leaf_Node we want to collapse
            """
            pass

        def manage_reg_ring():
            """
            A function that takes care of managing a ring on the leaves that prevents further cropping because
            of a ring of "regulates structure, for instance like in a feed-back loop.

            - Removes all the regulates relations and computes the regulation-less leafs
            - Finds clusters of reg-less listst that are connex through "regulates" and "Up" relations
            - For each cluster, copies to each node a list of all reachable nodes from the main cluster

             Also calls from the outer scope:
                * Structure: dict of Forward Up and Reg links separaterly # used to build a partial connexity matrix
                *

            """
            # Implementation spec: use scipy.sparse.csgraph.shortest_path on a graph with progressively more and more
            # fractured "regulates" links
            pass


        for node in Leaves:
            pass

    def build_laplacian(self, include_reg=True):
        """
        Builds undirected laplacian matrix for the GO transitions. This one actually depends on the get_GO reach command

        :warning: for this method to function, get_GO reach function must be run first.

        :param include_reg: if True, regulation transitions will be included.
        """
        pass

    def get_GO_Informativities(self):
        """
        Here calculated without any information on regulation
        ..todo: introduce the iformation computation with regulation,. Outiline: transmit to each higher-level node the
                number of nodes attainable from each node. I.e. instead of an exploration rooted at each node, use
                a simultaneous exploration of a whole tree.

        """
        i = 0
        l = len(self.UP2GO_Dict)
        for key in self.UP2GO_Dict.keys():
            i += 1
            print 'entering', float(i)/float(l), self.time()
            toVisit = copy.copy(self.UP2GO_Dict[key])
            visited = []
            while toVisit:
                elt = toVisit.pop()
                vs = acceleratedInsert(self.UP2GO_Dict, self.accelerationDict, elt)
                visited += vs
            visited = list(set(visited))
            for elt in visited:
                if elt not in self.TimesReached.keys():
                    self.Reverse_Dict[elt] = []
                    self.TimesReached[elt] = 0
                self.Reverse_Dict[elt].append(key)
                self.TimesReached[elt] += 1
        # Fle=file('GO_Informativities.dump','w')
        # pickle.dump(TimesReached,Fle)  #TODO": correct dumping here
        # Fle2=file('accDict.dump','w')
        # pickle.dump(accelerationDict,Fle2)  #TODO": correct dumping here
        # Fle3=file('Reverse_dict.dump','w')
        # pickle.dump(Reverse_Dict, Fle3)  #TODO": correct dumping here


    def compute_UniprotDict(self):
        """


        :return:
        """
        UniprotDict = {}
        for elt in MG.Uniprots:
            node = DatabaseGraph.UNIPORT.get(elt)
            altID = node.ID
            UniprotDict[altID] = (elt, MG.ID2displayName[elt])
            UniprotDict[elt] = altID
        pickle.dump(UniprotDict, file(Dumps.Up_dict_dump,'w'))
        return UniprotDict


if __name__ == '__main__':
    filtr = ['biological_process']

    KG = GO_Interface(filtr, MG.Uniprots)
    KG.rebuild()
    KG.store()

    # KG.load()
    # KG.get_GO_Reach()