import sys
import random
import numpy as np
import numpy.ma as ma
import networkx as nx

class DrugTarget(object):
    def __init__(self, dt="DrugTargetNetwork.txt"):
        self.d2t = {}
        with open(dt) as fi:
            for line in fi:
                d, t = line.strip("\n").split("\t")
                self.d2t.setdefault(d, []).append(t)
        self.drugs = sorted(self.d2t)

    def Screen(self, genes, repeat):
        interactome = Interactome(binSize=100)
        genes = interactome.Name2Index(genes)
        for drug in self.drugs:
            targets = interactome.Name2Index(self.d2t[drug])
            if targets:
                d, z, p = interactome.ProximityZ(targets, genes, repeat=repeat)
                print(drug, " D: %.3f  Z: %s%.3f  P: %.3f" % (d, "" if z < 0 else " ", z, p))


class Interactome(object):
    def __init__(self, pathG="proximity/HumanInteractome.tsv", pathSD="proximity/HumanInteractome.npy", binSize=300):
        self.G = nx.read_edgelist(pathG, delimiter="\t", data=[("src", str), ("typ", str)])
        self.G.remove_edges_from(nx.selfloop_edges(self.G))
        self.SD = np.load(pathSD, allow_pickle=True)
        self.nodes = sorted(self.G.nodes())
        self.i2n = {index: node for index, node in enumerate(self.nodes)}
        self.n2i = {node: index for index, node in enumerate(self.nodes)}
        self.i2d = {}
        self.d2i = {}
        for node, degree in self.G.degree():
            index = self.n2i[node]
            if degree in self.d2i:
                self.d2i[degree].append(index)
            else:
                self.d2i[degree] = [index]
            self.i2d[index] = degree
        self.dmin = min(self.d2i.keys())
        self.dmax = max(self.d2i.keys())
        # ------------------------------
        self.binSize = binSize
        self.d2b = {}
        self.b2i = {}
        self.d2b = {}
        self.b2i = {0: []}
        degrees = sorted(self.d2i.keys())
        b = 0
        for curr, till in zip(degrees, degrees[1:] + [degrees[-1] + 1]):
            for d in range(curr, till):
                self.d2b[d] = b
            self.b2i[b].extend(self.d2i[curr])
            if curr != degrees[-1] and len(self.b2i[b]) >= binSize:
                b += 1
                self.b2i[b] = []
        if len(self.b2i[b]) < binSize and b > 0:
            for d in range(degrees[-1], -1, -1):
                if self.d2b[d] != b:
                    break
                self.d2b[d] = b - 1
            self.b2i[b - 1].extend(self.b2i[b])
            del self.b2i[b]

    def Name2Index(self, names, skipUnknown=True):
        if skipUnknown:
            return [self.n2i[n] for n in names if n in self.n2i]
        else:
            return [self.n2i[n] for n in names]

    def DegreePreserveSampling(self, indexes):
        b2n = {}
        for index in indexes:
            b = self.d2b[max(self.dmin, min(self.dmax, self.i2d[index]))]
            if b not in b2n:
                b2n[b] = 0
            b2n[b] += 1
        for b in b2n:
            if b2n[b] > len(self.b2i[b]):
                raise ValueError("Number to sample > size of bin. Try to increase binSize")
        while True:
            yield sum([random.sample(self.b2i[b], b2n[b]) for b in sorted(b2n)], [])

    def Proximity(self, mod1, mod2):
        SD = self.SD[np.ix_(mod1, mod2)]
        closest1 = SD.min(0)
        closest2 = SD.min(1)
        return (closest1.sum() + closest2.sum()) / (closest1.count() + closest2.count())
    
    def Distance(self, modDrug, modDisease): # function 1 in Feixiong Cheng et al. 2019
        # ZS: modified the code from Yadi Zhou. Function parameters from SD, mod1, mod2 to self, mod1, mod2
        return self.SD[np.ix_(modDrug, modDisease)].min(0).mean()

    def ProximityRandom(self, mod1, mod2, repeat, method="closest"):
        result = np.zeros(repeat)
        index = 0
        for mod1r, mod2r in zip(self.DegreePreserveSampling(mod1), self.DegreePreserveSampling(mod2)):
            if method == 'closest':
                v = self.Proximity(mod1r, mod2r)
            elif method == 'distance':
                v = self.Distance(mod1r, mod2r)
            if not ma.is_masked(v):
                result[index] = v
                index += 1
                if index == repeat:
                    break
        return result

    def ProximityZ(self, mod1, mod2, repeat, method="closest"): 
        if method == 'closest':
            print("Calculating proximity using closest method")
            d = self.Proximity(mod1, mod2)
            b = self.ProximityRandom(mod1, mod2, repeat=repeat)
            z, p = Z_Score(d, b)
        elif method == 'distance':
            print("Calculating proximity using distance method")
            d = self.Distance(mod1, mod2)
            b = self.ProximityRandom(mod1, mod2, repeat=repeat, method="distance")
            z, p = Z_Score(d, b)
        return d, z, p, b


def Z_Score(real, background):
    m = background.mean()
    s = background.std(ddof=1)
    z = (real - m) / s
    p = np.mean(background < real)
    return z, p
