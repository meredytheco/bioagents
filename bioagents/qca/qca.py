# QCA stands for qualitative causal agent whose task is to
# identify causal paths within

import os
import logging
#from indra.statements import ActiveForm
#from indra.bel.processor import BelProcessor
import json
import ndex.client as nc
import requests
import io
from enum import Enum
from ndex.beta.path_scoring import PathScoring

logger = logging.getLogger('QCA')

_resource_dir = os.path.dirname(os.path.realpath(__file__)) + '/../resources/'

class PathNotFoundException(Exception):
    def __init__(self, *args, **kwargs):
            Exception.__init__(self, *args, **kwargs)

class QCA:
    def __init__(self):
        logger.debug('Starting QCA')
        self.host = "http://www.ndexbio.org"

        self.results_directory = "qca_results"

        self.directed_path_query_url = 'http://general.bigmech.ndexbio.org:5603/directedpath/query'
        #self.directed_path_query_url = 'http://localhost:5603/directedpath/query'

        self.context_expression_query_url = 'http://general.bigmech.ndexbio.org:8081/context/expression/cell_line'

        self.context_mutation_query_url = 'http://general.bigmech.ndexbio.org:8081/context/mutation/cell_line'

        # dict of reference network descriptors by network name
        self.reference_networks_full = [
            {
                "id": "84f321c6-dade-11e6-86b1-0ac135e8bacf",  # "84f321c6-dade-11e6-86b1-0ac135e8bacf",
                "name": "Calcium signaling in the CD4 TCR pathway",
                "type": "cannonical"
            }
        ]

        self.reference_networks_ful = [
            {
                "id": "5294f70b-618f-11e5-8ac5-06603eb7f303",
                "name": "Calcium signaling in the CD4 TCR pathway",
                "type": "cannonical"
            },
            {
                "id": "5e904cd6-6193-11e5-8ac5-06603eb7f303",
                "name": "IGF1 pathway",
                "type": "cannonical"
            },
            {
                "id": "20ef2b81-6193-11e5-8ac5-06603eb7f303",
                "name": "HIF-1-alpha transcription factor network ",
                "type": "cannonical"
            },
            {
                "id": "ac39d2b9-6195-11e5-8ac5-06603eb7f303",
                "name": "Signaling events mediated by Hepatocyte Growth Factor Receptor (c-Met)",
                "type": "cannonical"
            },
            {
                "id": "d3747df2-6190-11e5-8ac5-06603eb7f303",
                "name": "Ceramide signaling pathway",
                "type": "cannonical"
            },
            {
                "id": "09f3c90a-121a-11e6-a039-06603eb7f303",
                "name": "NCI Pathway Interaction Database - Final Revision - Extended Binary SIF",
                "type": "cannonical"
            },
            {
                "id": "50e3dff7-133e-11e6-a039-06603eb7f303",
                "name": "The Ras machine",
                "type": "non-cannonical"
            }
        ]

        # --------------------------
        # Schemas

        self.query_result_schema = {
            "network_description": {},
            "forward_paths": [],
            "reverse_paths": [],
            "forward_mutation_paths": [],
            "reverse_mutation_paths": []
        }

        self.reference_network_schema = {
            "id": "",
            "name": "",
            "type": "cannonical"
        }

        self.query_schema = {
            "source_names": [],
            "target_names": [],
            "cell_line": ""
        }

        # dict of available network CX data by name
        self.loaded_networks = {}

        # --------------------------
        #  Cell Lines

        self.cell_lines = []

        # --------------------------
        #  Queries

        # list of query dicts
        self.queries = []

        self.ndex = nc.Ndex(host=self.host)

        self.load_reference_networks()

    def __del__(self):
        print "deleting class"
        #self.drug_db.close()

    def find_causal_path(self, source_names, target_names, exit_on_found_path=False, relation_types=None):
        '''
        Uses the source and target parameters to search for paths within predetermined directed networks.
        :param source_names: Source nodes
        :type source_names: Array of strings
        :param target_names: Target nodes
        :type target_names: Array of strings
        :param exit_on_found_path: Used for has_path()
        :type exit_on_found_path: Boolean
        :param relation_types: Edge types
        :type relation_types: Array of strings
        :return: Edge paths
        :rtype: Array of tuples
        '''
        results_list = []

        #==========================================
        # Find paths in all available networks
        #==========================================
        for key in self.loaded_networks.keys():
            pr = self.get_directed_paths_by_names(source_names, target_names, self.loaded_networks[key], relation_types=relation_types, max_number_of_paths=50)
            prc = pr.content
            #==========================================
            # Process the data from this network
            #==========================================
            if prc is not None and len(prc.strip()) > 0:
                try:
                    result_json = json.loads(prc)
                    if result_json.get('data') is not None and result_json.get("data").get("forward_english") is not None:
                        f_e = result_json.get("data").get("forward_english")

                        results_list += [f_e_i for f_e_i in f_e if len(f_e) > 0]
                        #============================================
                        # Return right away if the exit flag is set
                        #============================================
                        if len(results_list) > 0 and exit_on_found_path:
                            return results_list
                except ValueError as ve:
                    print "value is not json.  html 500?"
        path_scoring = PathScoring()
        #results_list_sorted = sorted(results_list, lambda x,y: self.path_length_ranking(x, y))  # 1 if len(x) > len(y) else -1 if len(x) < len(y) else 0)
        results_list_sorted = sorted(results_list, lambda x,y: path_scoring.cross_country_scoring(x, y))

        return results_list_sorted[:50]


    def cross_country_ranking(self, x, y):
        edge_ranking = EdgeRanking()

        possible_placement = {}
        for i in range(1, EdgeEnum.edge_count()):
            possible_placement[i] = []

        for index, xi in enumerate(x):
            if(type(xi) is list):
                if(len(xi) > 0 and "interaction" in xi[0]):
                    edge_type = xi[0]["interaction"]
                    position = edge_ranking.edge_type_rank[edge_type]
                    possible_placement[position].append("x")
            elif(type(xi) is str):
                s = ""
            else:
                s = ""

        return 0

    def path_length_ranking(self, x, y):
        if len(x) > len(y):
            return 1
        elif len(x) < len(y):
            return -1
        else:
            return 0

    def has_path(self, source_names, target_names):
        '''
        determine if there is a path between nodes within predetermined directed networks
        :param source_names: Source nodes
        :type source_names: Array of strings
        :param target_names: Target nodes
        :type target_names: Array of strings
        :return: Path exists
        :rtype: Boolean
        '''
        found_path = self.find_causal_path(source_names, target_names, exit_on_found_path=True)

        return len(found_path) > 0

    def load_reference_networks(self):
        for rn in self.reference_networks_full:
            if "id" in rn and "name" in rn:
                result = self.ndex.get_network_as_cx_stream(rn["id"])
                self.loaded_networks[rn["name"]] = result.content #json.loads(result.content)

            else:
                raise Exception("reference network descriptors require both name and id")

    def get_directed_paths_by_names(self, source_names, target_names, reference_network_cx, max_number_of_paths=5, relation_types=None):
        #====================
        # Assemble REST url
        #====================
        target = ",".join(target_names)
        source = ",".join(source_names)
        if relation_types is not None:
            rts = " ".join(relation_types)
            url = self.directed_path_query_url + '?source=' + source + '&target=' + target + '&pathnum=' + str(max_number_of_paths) + '&relationtypes=' + rts
        else:
            url = self.directed_path_query_url + '?source=' + source + '&target=' + target + '&pathnum=' + str(max_number_of_paths)

        f = io.BytesIO()
        f.write(reference_network_cx)
        f.seek(0)
        r = requests.post(url, files={'network_cx': f})
        return r

    def get_path_node_names(self, query_result):
        return None

    def get_expression_context(self, node_name_list, cell_line_list):
        query_string = " ".join(node_name_list)
        params = json.dumps({query_string: cell_line_list})
        r = requests.post(self.context_expression_query_url, json=params)
        return r

    def get_mutation_context(self, node_name_list, cell_line_list):
        query_string = " ".join(node_name_list)
        params = json.dumps({query_string: cell_line_list})
        r = requests.post(self.context_mutation_query_url, json=params)
        return r

    def save_query_results(self, query, query_results):
        path = self.results_directory + "/" + query.get("name")
        outfile = open(path, 'wt')
        json.dump(query_results,outfile, indent=4)
        outfile.close()

    def get_mutation_paths(self, query_result, mutated_nodes, reference_network):
        return None

    def create_merged_network(self, query_result):
        return None

    def run_query(self, query):
        query_results = {}

        for network_descriptor in self.reference_networks:
            query_result = {}
            network_name = network_descriptor["name"]
            cx = self.loaded_networks[network_descriptor["id"]]
            # --------------------------
            # Get Directed Paths
            path_query_result = self.get_directed_paths_by_names(query["source_names"], query["target_names"], cx)
            path_node_names = self.get_path_node_names(path_query_result)
            query_result["forward_paths"] = path_query_result["forward_paths"]
            query_result["reverse_paths"] = path_query_result["reverse_paths"]

            # --------------------------
            # Get Cell Line Context for Nodes
            context_result = self.get_mutation_context(path_node_names, list(query["cell_line"]))
            mutation_node_names = []

            # --------------------------
            # Get Directed Paths from Path Nodes to Mutation Nodes
            # (just use edges to adjacent mutations for now)
            # (skip mutation nodes already in paths)
            mutation_node_names_not_in_paths = list(set(mutation_node_names).difference(set(path_node_names)))
            mutation_query_result = self.get_directed_paths_by_names(path_node_names, mutation_node_names_not_in_paths, cx)
            query_result["forward_mutation_paths"] = mutation_query_result["forward_paths"]
            query_result["reverse_mutation_paths"] = mutation_query_result["reverse_paths"]

            # --------------------------
            # Annotate path nodes based on mutation proximity, compute ranks.

            # --------------------------
            # Build, Format, Save Merged Network
            merged_network = None

            # --------------------------
            # Contrast and Annotate Canonical vs Novel Paths
            # Cannonical Paths
            # Novel Paths
            # Cannonical Paths not in general networks
            # Add summary to result

            query_results[network_name] = query_result

        # --------------------------
        # Save Query Results (except for network)
        self.save_query_results(query_results)

        return None

    # --------------------------
    #  Load Reference Networks

    # --------------------------
    #  Run Queries
    #
    # for query in queries:
    #     run_query(query)

class EdgeRanking:
    def __init__(self):
        self.edge_types = []

        self.edge_class_rank = {
            EdgeEnum.specific_protein_protein: [  # 1
                "controls-transport-of",
                "controls-phosphorylation-of",
                "Phosphorylation",
                "Dephosphorylation",
                "controls-transport-of-chemical",
                "consumption-controled-by",
                "controls-production-of"
            ],
            EdgeEnum.unspecified_activation_inhibition: [  # 2
                "Activation",
                "Inhibition"
            ],
            EdgeEnum.unspecified_state_control: [  # 3
                "controls-state-change-of",
                "chemical-affects"
            ],
            EdgeEnum.unspecified_direct: [  # 4
                "reacts-with",
                "used-to-produce"
            ],
            EdgeEnum.transcriptional_control: [  # 5
                "controls-expression-of"
            ],
            EdgeEnum.proteins_catalysis_lsmr: [  # 6
                "catalysis-precedes"
            ],
            EdgeEnum.specific_protein_protein_undirected: [  # 7
                "in-complex-with",
                "Complex"
            ],
            EdgeEnum.non_specific_protein_protein_undirected: [  # 8
                "interacts-with"
            ],
            EdgeEnum.unspecified_topological:[  # 9
                "neighbor-of"
            ]
        }

        #===============================================
        # Generates a dict based on edge_class_rank
        # with edge types as key and rank int as value
        #===============================================
        self.edge_type_rank = {}

        for key in self.edge_class_rank.keys():
            for et in self.edge_class_rank[key]:
                self.edge_type_rank[et] = key.value

    def build_edge_type_list(self, edge_class_type_array):
        for ect in edge_class_type_array:
            if(type(ect) is EdgeEnum):
                for et in self.edge_class_rank[ect]:
                    if(et not in self.edge_types):
                        self.edge_types.append(et)

    def print_edge_types(self):
        for et in self.edge_types:
            print et

#==================================
# Enum Classes
#==================================
class EdgeEnum(Enum):
    specific_protein_protein = 1
    unspecified_activation_inhibition = 2
    unspecified_state_control = 3
    unspecified_direct = 4
    transcriptional_control = 5
    proteins_catalysis_lsmr = 6  # linked small molecule reactions
    specific_protein_protein_undirected = 7
    non_specific_protein_protein_undirected = 8
    unspecified_topological = 9

    def edge_count(self):
        return 9
