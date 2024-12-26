# -*- coding: utf-8 -*-
# Author: Yadi Zhou

import sys
import random
from proximity import DrugTarget
from proximity import Interactome

if __name__ == "__main__":
    input1 = sys.argv[1]
    input2 = sys.argv[2]
    repeat = int(sys.argv[3])
    random.seed(int(sys.argv[4]))

    if input1 == "DRUG":
        with open(input2) as fi:
            genes = fi.read().splitlines()
        dt = DrugTarget()
        dt.Screen(genes, repeat=repeat)
    else:
        with open(input1) as fi:
            genes1 = fi.read().splitlines()
        with open(input2) as fi:
            genes2 = fi.read().splitlines()
        interactome = Interactome(binSize=200)
        genes1 = interactome.Name2Index(genes1)
        genes2 = interactome.Name2Index(genes2)
        d, z, p, b = interactome.ProximityZ(genes1, genes2, repeat=repeat, method="distance")
        print("D: %.3f  Z: %s%.3f  P: %.3f" % (d, "" if z < 0 else " ", z, p))
        
        # generate ggplot2 ready csv result for visualization. This csv has three columns: Value,Type {'Real', 'Background'},Permutation_ID
        # initialize an empty df
        import pandas as pd
        df = pd.DataFrame(columns=['Value', 'Type'])
        # add a row for the real value, do not use append
        df.loc[0] = [d, 'Real']
        # add rows for the background values
        for i in range(len(b)):
            df.loc[i+1] = [b[i], 'Background']
        # save the df as a csv
        output = 'Perm_' + input1.split('.')[0] + '-Distance-' + input2.split('.')[0] + '.csv'
        df.to_csv(output, index=False)

        # write # "D: %.3f  Z: %s%.3f  P: %.3f" % (d, "" if z < 0 else " ", z, p) to output file as the first line
        with open(output, 'r') as original: data = original.read()
        with open(output, 'w') as modified: modified.write("# D: %.3f  Z: %s%.3f  P: %.3f\n" % (d, "" if z < 0 else " ", z, p) + data)
