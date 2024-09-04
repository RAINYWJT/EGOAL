import os
import sys, getopt
import pandas as pd
import joblib
import glob
import re
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

#from concept_extract.term_embd import graph_parse
#from concept_extract.txt2con import EmbeddingConverter


def main(argv):

    ''' parse in & out arg '''

    in_pth = 'predict/input.txt'
    out_dir = 'predict/results'
    n_inputs = 0
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","odir="])
    except getopt.GetoptError:
        print ('test.py -i <input_dir> -o <output_dir>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('test.py -i <input_file> -o <output_dir>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            in_pth = arg
        elif opt in ("-o", "--odir"):
            out_dir = arg

    
    ##################################################

    ''' initialize text embedding model '''
    os.environ["http_proxy"] = "http://127.0.0.1:7890"
    os.environ["https_proxy"] = "http://127.0.0.1:7890"
    embd_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    ''' initialize text embeddings of concepts '''
    goa_df = pd.read_csv('rules/goa_gene2go_filtered.csv', header=None, index_col=0)
    con_embd = np.load('dataset/embedding/go_txt_embd.npy')
    con_embd_idx = []
    with open('dataset/embedding/go_embd_idx.txt', 'r') as f:
        con_embd_idx = eval(f.readline())
    
    ''' initialize concept lists '''
    TOP_CNT = 10
    concepts = []
    
    ''' read descriptions from input file '''
    descriptions = []
    with open(in_pth, 'r') as f:
        descriptions = f.readlines()
        n_inputs = len(descriptions)
    
    ''' iterate instances '''
    for d in tqdm(descriptions, 'processing input instance'):
    
            ''' compute similarity matrix & most similar concept list '''
            #sim = embd.similar_matrix(d)
            text_embd = embd_model.encode([d])
            sim = embd_model.similarity(con_embd, text_embd)
            sorted_sim, sorted_term = zip(*sorted(zip(sim, con_embd_idx), reverse=True))
            #sorted_sim = embd.max_sim(TOP_CNT)
            sorted_term = sorted_term[:TOP_CNT]
    
            concepts.append(list(sorted_term))
    
    
    ''' load gene - product mapping '''
    gene_mapping = {}
    with open('predict/gene_mapping.txt', 'r') as f:
        gene_mapping = eval(f.readline())
    
   ################################################## 
    
    ''' load pretrained model for each single gene '''
    models = []
    name_list = []
    model_files = glob.glob('models/SO_*_model.joblib')
    for gene_id in tqdm(range(1, 4759)):
        model_file = f'models/SO_{gene_id:04d}_model.joblib'
        name_list.append(f'SO_{gene_id:04d}')
        if model_file in model_files:
            model = joblib.load(model_file)
            models.append(model)
        else:
            models.append(None)  
    
    ''' predict for each input with pretrained model '''
    for i in tqdm(range(n_inputs), 'processing input'):
        concept_ids = [int(re.sub(r'GO_0*', '', c)) for c in concepts[i]]
        
        predictions = []
        for model in models:
            if model is not None:
                prediction = model.predict_proba([concept_ids])[0]
                predictions.append(prediction)
            else:
                predictions.append([0,0])  
        
        ''' zip name & pred prob as lst '''
        result = [(name, pred[1]) for name, pred in zip(name_list, predictions) if pred[1] > .5]
        result.sort(key= lambda x: x[1], reverse=True)
        
        with open(f'{out_dir}/res_{i}.txt', 'w') as f:
            f.write('gene id\tconfidence\tproduct\n')
            for g in result:
                prod = gene_mapping[g[0]]
                #if 'unknown' in prod or 'uncharacterized' in prod:
                #    continue
                if g[0] not in goa_df.index:
                    print(g)
                    continue
    
                f.write(f'{g[0]}\t{g[1]:.2f}\t{gene_mapping[g[0]]}\n')

        #tmp
        break

    ##################################################

if __name__ == "__main__":
    main(sys.argv[1:])
