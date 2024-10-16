"""Used to measure presence of carbohydrate on structure.

    Usage
    =====
        ./glyco_diy.py -top <topology_file> -trj <trajectory_file> -output <file_name> -threshold <threshold_interaction>
"""

__author__ = "Ravy LEON FOUN LIN"
__date__ = "03 - 10 - 2024"

import argparse
import sys
import numpy as np
import pandas as pd
from glob import glob
from tqdm import tqdm
import MDAnalysis as mda
from MDAnalysis.analysis.distances import distance_array
from Bio.PDB import PDBParser, PDBIO
import pickle as pkl

parser = argparse.ArgumentParser(prog = 'Glyco if it was actually smart coded',
                                 description = """Compute frequence of interaction by carbohydrate on protein, and set it in new PDB structure as b-factor values.
                                 It produce a csv file, indicating which residue interact with which carbohydrate and how many times. The count is raw.
                                 And as many PDB files as the number of carbohydrates in the topology.
                                 """)
parser.add_argument("-top",help="Path to topology file.")
parser.add_argument("-trj",help="Path to trajectory file.")
parser.add_argument("-output",help="Path to output file.")
parser.add_argument("-threshold",help="Threshold of contact.")


args = parser.parse_args()

if args.top == None or args.trj == None or args.output == None or args.threshold == None :
    parser.print_help()
    sys.exit()
else :
    TOP = args.top
    TRJ = args.trj
    OUT = args.output
    THR = args.threshold

def Universe(TOP : str,TRJ : str) :
    """Set Universe.

        Parameters
        ----------
            TOP : str
                Path to topology file.
            TRJ : str
                Path to trajectory file(s).
    
        Returns
        -------
            Universe (MDAnalysis object.)
    """

    #  Define Universe.
    u = mda.Universe(TOP,TRJ)

    return u


def create_dictionnary(u) :
    """Create Dictionnary of count.

        Parameters
        ----------
            u : MDAnalysis object.
        
        Returns
        -------
            Dictionnary
            Format : {"Carbohydrate_ID" : {'residue':count,...}}
    """

    #  Create empty dictionnary.
    dict_carbs = {}

    #  Fullfill with carbohydrate segid as key and dict of amino acid as values.
    for segment in u.segments :

        #  Get ID treated.
        ID = segment.segid

        #  Check if it is carb
        if ID[:3] == 'CAR' :
            #  Create key-value
            dict_carbs[ID] = {}

    #  Return dict.
    return dict_carbs


def fullfill_dict(THR : str, dict_carbs : dict) :
    """Count contact of carbohydrate and fullfil dict.

        Parameters
        -----------
            THR : str
                Threshold to count contact.
            dict_carbs : dict
                Dict of count.
            
        Returns
        -------
            Dict
            Fullfill dictionnary.
    """

    #  Create list of input for carbohydrates.
    input_carbs_list = list()
    for carbs in dict_carbs.keys() :
        INPUT = u.select_atoms(f"segid {carbs}")
        input_carbs_list.append(INPUT)
    
    #  Select C-alpha from protein.
    protein = u.select_atoms("name CA")

    for ts in tqdm(u.trajectory) :
        for atom in protein :
            for carbs in input_carbs_list :
                d = distance_array(carbs.positions,atom.position)[0][0]
                if d <= THR :
                    key = f"{atom.residue.resname}_{atom.residue.resid}_{atom.segid}"
                    if key not in dict_carbs[carbs.segids[0]].keys() :
                        dict_carbs[carbs.segids[0]][key] = 1
                    else :
                        dict_carbs[carbs.segids[0]][key] += 1
                else :
                    continue
    
    #  Save as dataframe.
    df = pd.DataFrame.from_dict(dict_carbs, orient = 'index')
    df.to_csv("out_count_carbohydrates.csv")

    return dict_carbs


def set_new_b_factor(TOP : str, new_b_factors : dict, length_sim : int, carb : str, OUT : str) :
    """New function to set new b-factors values.

        Parameters
        ----------
            TOP : str
                Path to topology file.
            new_b_factors : dict
                Dict which contains count of interaction with carbohydrates?
            length_sim : int
                Duration of the simulation in frame.
            carb : str
                Carbohydrate segid treating.
            OUT : str
                Path to output.

        Returns
        -------
            Write a new file.
    """

    #  Name output.
    output_pdb = f"${OUT}/contact_with_{carb}.pdb"

    #  Set parser.
    parser = PDBParser(QUIET=True)

    #  Parser structure.
    structure = parser.get_structure("protein",TOP)

    #  Full fill dictionnary
    for model in structure :
        for chain in model :
            chain_id = chain.get_id()
            for residue in chain :
                #  Retrieve infos to write the name.
                resid = residue.get_id()[1]
                resn = residue.resname
                segid = residue.segid
                name = f"{resn}_{resid}_{segid}"
                if name in new_b_factors[carb].keys() :
                    #  Count percentage of interaction through the simulation.
                    new_bfs = (new_b_factors[carb][name]/length_sim)*100
                    
                    #  Round the value with three numbers.
                    new_bfs = round((new_bfs),3)
                    
                    print(new_bfs)
                else :
                    #  This value is set for the residues which never interact with carbohydrates.
                    new_bfs = -1.00
                #  Set the new
                for atom in residue :
                    atom.set_bfactor(new_bfs)

    #  Save new structure.
    io = PDBIO()
    io.set_structure(structure)
    io.save(output_pdb)

    return 0              


if __name__ == "__main__" :
    #  Load universe object...
    print("Load Universe...")
    u = Universe(TOP,TRJ)
    
    #  Create dictionnary for new b_factors.
    print("Create dictionnary...")
    dictionnary = create_dictionnary(u)

    #  Compute contact of carbohydrates with threshold setted.
    print("Fullfill dictionnary...")
    THR = int(THR)
    full_dict = fullfill_dict(THR, dictionnary)

    #  Frames number.
    full_time = (u.trajectory.totaltime)+1

    #  Creation of new structure with new b_factors for each carbohydrates?
    for carb in full_dict.keys() :
        print(f"Treating {carb}...")
        set_new_b_factor(TOP, full_dict, full_time, carb, OUT)
