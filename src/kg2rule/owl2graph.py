from operator import index
from rdflib import Graph
import pandas as pd
import os
import re
import numpy as np
from scipy.integrate._ivp.radau import P
from tqdm import tqdm

from mining import ruleTranslate
from remember import resolve

def extrID(s):
    s = str(s)

    idx = 0
    for i in range(len(s)):
        if s[i] == '/':
            idx = i+1
    s = s[idx:]

    return s

##################################################

class KG2Rule():

    def __init__(self, rdf_pth, con_spec_pth :str, owl_pth = '') -> None:
        if not os.path.exists(rdf_pth):
            if owl_pth=='':
                raise Exception('Need specify path to OWL file when owl is not parsed.')

            self.__readOWL(owl_pth, rdf_pth)

        self.rdf = pd.read_csv(rdf_pth)

        self.rdf['subject'] = self.rdf['subject'].apply(extrID)
        self.rdf['predicate'] = self.rdf['predicate'].apply(extrID)
        self.rdf['object'] = self.rdf['object'].apply(extrID)

        self.rule_set = None
        self.con_spec = list(pd.read_csv(con_spec_pth, header=None)[0])



    def __readOWL(self, owl_pth :str, out_pth :str):
        '''
        read owl file as rdf graph
        '''

        g = Graph()
        g.parse(owl_pth)
        
        # Create Dict of s,p,o
        df = {'subject':[], 'predicate':[], 'object':[]}
        for s,p,o in tqdm(g, 'Parsing OWL File'):
            df['subject'].append(s)
            df['predicate'].append(p)
            df['object'].append(o)
        
        df = pd.DataFrame(df)
        df.to_csv(out_pth, index=False)

    
    ##################################################


    def subGraph(self, exclude_prdc_pth: str, d :int) -> pd.DataFrame:
        '''
        Exclude Unused Predicates, and
        Extract Subgraph from parsed RDF (ABL-KG chap 4.3)
        '''

        exclude_prdc = list(pd.read_csv(exclude_prdc_pth, header=None)[0])

        mask = ~ self.rdf['predicate'].isin(exclude_prdc)
        self.rdf = self.rdf[mask]
        self.rdf.reset_index(drop=True, inplace=True)

        print('----- Statics of Filtered Predicates -----')
        print(self.rdf.groupby(by='predicate').count(), '\n')
        # TODO: handle most fraquent predicates: owl#annotatedProperty & owl#annotatedSource


        print('----- Extracting Subgraph -----')
        node_expand = self.con_spec
        node_succ   = []
        mask = [False]*len(self.rdf)
        for i in range(d):
            for idx, row in tqdm(self.rdf.iterrows(), 'Round '+str(i+1)):
                if mask[idx]:
                    continue

                if row['subject'] in node_expand:
                    node_succ.append(row['object'])
                    mask[idx] = True
                #elif row['object'] in node_expand:
                #    node_succ.append(row['subject'])
                #    mask[idx] = True

            node_expand = node_succ
            node_succ = []


        self.rdf = self.rdf[mask]
        self.rdf.reset_index(drop=True, inplace=True)
        print('Extracted Subgraph:\n', self.rdf)

        print('----- Statics of Subgraph Predicates -----')
        print(self.rdf.groupby(by='predicate').count(), '\n')

        return self.rdf



    def mineRule(self, rdf = pd.DataFrame()) -> pd.DataFrame:
        '''
        Call rule translation to convert all RDF predicates to Horn Clauses,
        according to natural semantic of predicates.
        '''
        if not rdf.empty:
            self.rdf = rdf

        print('----- Rule mining with translation rules -----')

        self.rule_set = set()
        for idx, row in self.rdf.iterrows():
            for r in ruleTranslate(row['subject'], row['predicate'], row['object']):
                self.rule_set.add(r)

        return pd.DataFrame({0: list(self.rule_set)})



    def remember(self, T:int, rule= []) -> pd.DataFrame:

        print('----- Forgetting unused rules -----')

        R_new = []
        if len(rule) > 0:
            self.rule_set = rule
            
        if self.rule_set == None:
            raise Exception('Need to specify rule set')


        for r in self.rule_set:
            if r[1] in self.con_spec or r[3] in self.con_spec:
                R_new.append(r)

        for t in range(T):
            R_res = []

            for r_new in tqdm(R_new, 'Round '+str(t+1)):
                for r in self.rule_set:
                    res = resolve(r_new, r, self.con_spec)
                    if res != None and res not in self.rule_set:
                        R_res.append(res)
                
            R_new = R_res
            for r in R_res:
                self.rule_set.add(r)

        rule_rem = [r for r in self.rule_set if (r[1] in self.con_spec and r[3] in self.con_spec)]
        self.rule_set = set(rule_rem)

        return pd.DataFrame({0: rule_rem})



##################################################


#    res = re.findall(r'GO_\d*', s)
#    if len(res) == 1:
#        return res[0]
#
#    res = re.findall(r'[BFR]{1,2}O_\d*', s)
#    if len(res) == 1:
#        return res[0]
#
#    res = re.findall(r'N\w{32}', s)
#    if len(res) == 1:
#        return np.NaN


if __name__ == '__main__':

    owlPth         = './rules/go.owl'
    rdfPth         = './rules/KG_RDF.csv'

    prdcLstPth         = 'rules/predicates.csv'
    exclPrdcPth     = 'rules/predicates_exclude.csv'
    conSpecPth      = 'dataset/concepts/concept_domain.csv'
    #filteredRdfPth  = './rules/KG_RDF_filter.csv'
    subGraphPth     = 'rules/KG_RDF_subgraph.csv'
    rulePth         = 'rules/ruleMined.csv'
    ruleRemPth      = 'rules/ruleRem.csv'

    graph = KG2Rule(rdfPth, conSpecPth, owlPth)

    #subGraphDf = graph.subGraph(exclPrdcPth, 5)
    #subGraphDf.to_csv(subGraphPth, index=False)

    ruleDf = graph.mineRule(rdf = pd.read_csv(subGraphPth))
    ruleDf.to_csv(rulePth, index=False, header=False)

    ruleDf = graph.remember(T=3)
    ruleDf.to_csv(ruleRemPth, index=False, header=False)


#def prdcFilter(s):
#    s = str(s)
#    prdc_to_rm = {'oboInOwl#hasDbXref', 'rdf-schema#label', 'IAO_0000233', 'RO_0002161',\
#                  'oboInOwl#default-namespace', '', '', '',\
#                 }
#
#    if s in prdc_to_rm :
#        return np.NaN
#
#    return s
#
#
#RDF = pd.DataFrame()
#RDF_filtered = pd.DataFrame()
#
#if not os.path.exists(rdfFile):
#
#
##GO_pattern = r'GO_\d+'
#GO_pattern = r'[GBFR]{1,2}O_\d+'
#
#RDF = pd.read_csv(rdfFile)
#
##mask = RDF['subject'].str.contains(GO_pattern) |\
##        RDF['object'].str.contains(GO_pattern) | RDF['predicate'].str.contains(GO_pattern)
##RDF = RDF[mask]
#
##mask = RDF['predicate'].str.contains(RO_pattern)
##RDF = RDF[mask]
#
#RDF.reset_index(drop=True, inplace=True)
#print(RDF)
#
#RDF['subject'] = RDF['subject'].apply(findID)
#RDF['object'] = RDF['object'].apply(findID)
#RDF['predicate'] = RDF['predicate'].apply(findID)
#RDF.dropna(subset=['subject', 'object'], inplace=True)
#
#predicates = list(set(RDF['predicate']))
#predicates = pd.Series(predicates)
#predicates.to_csv(prdcFile, index=False, header=False)
#
#print(RDF)
#RDF.to_csv(rdfFile_filtered, index=False)