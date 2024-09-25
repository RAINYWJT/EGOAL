import textwrap
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from tqdm import tqdm
from gene_merge import merge, merge_nodes
from gene_adjust import adjust

edges = {}
with open('plots/regu_graph/gene_graph', 'r') as f:
    edges = eval(f.readline())

goa_df = pd.read_csv('rules/goa_gene2go.csv', index_col=0, header=None)

gene_embd = np.load('plots/regu_graph/gene_embd_pca.npy')
gene_embd = gene_embd.transpose()
gene_df = pd.DataFrame({'pca0': gene_embd[0], 'pca1': gene_embd[1]}, index=goa_df.index)

res_df = pd.read_csv('predict/results/res_NADK.txt', sep='\t')
gene_res = set(res_df['gene_id'])
gene_id = list(res_df['gene_id'])
gene_product = list(res_df['product'])
gene_labels = {gene_id[i]: gene_product[i] for i in range(len(gene_id))}

G = nx.DiGraph()

# initial_nodes = []
# initial_edges = []

node_category = {}
# 添加节点及其坐标
for gene, pca_pos in tqdm(gene_df.iterrows(), total=len(gene_df)):
    if gene in gene_res:
        # G.add_node(gene)
        G.add_node(gene, pos=(pca_pos['pca0'], pca_pos['pca1']))  # 用pca数据作为坐标
        # initial_nodes.append(gene)

# 添加边
for gene, neighbors in tqdm(edges.items()):
    for neighbor in neighbors:
        if gene in gene_res and neighbor in gene_res:
            # initial_edges.append([gene, neighbors])
            if neighbor != gene:
                G.add_edge(gene, neighbor)
            else:
                node_category[gene] = 'class1'
    if gene not in node_category:
        node_category[gene] = 'class2'

# merge_list = merge(initial_nodes, initial_edges)

# G = merge_nodes(G, merge_list)

G = adjust(G)
nodes_list = list(G.nodes())
union_node = set()
for i in range(len(nodes_list)):
    for j in range(i + 1, len(nodes_list)):
        node_i = nodes_list[i]
        node_j = nodes_list[j]
        if node_i == node_j:
            continue
        pos_i = G.nodes[node_i].get('pos', [])
        pos_j = G.nodes[node_j].get('pos', [])
        if len(pos_i) > 0 and len(pos_j) > 0 and all(x == y for x, y in zip(pos_i, pos_j)):
            if [node_i, node_j] in G.edges and [node_j, node_i] in G.edges:
                new_node = node_i + "<->" + node_j
            elif [node_i, node_j] in G.edges:
                new_node = node_i + "->" + node_j
            elif [node_j, node_i] in G.edges:
                new_node = node_i + "<-" + node_j
            else:
                new_node = node_i + "," + node_j
            G.add_node(new_node, pos=(G.nodes[node_i]['pos']))
            for neighbor in set(G.successors(node_i)).union(G.successors(node_j)):
                G.add_edge(new_node, neighbor)
            for predecessor in set(G.predecessors(node_i)).union(G.predecessors(node_j)):
                if predecessor != new_node:
                    G.add_edge(predecessor, new_node)
            union_node.add(node_i)
            union_node.add(node_j)
            node_category[new_node] = 'class3'

for node in union_node:
    G.remove_node(node)

color_map = {'class1': 'green', 'class2': 'red', 'class3': 'blue'}
node_colors = [color_map[node_category[node]] for node in G.nodes()]

# 获取节点位置
pos = nx.get_node_attributes(G, 'pos')

plt.figure(figsize=(24, 12))

plt.subplot(1, 2, 1)

plt.suptitle('Gene Network Graph', fontsize=30)

nx.draw(G, pos, with_labels=False, node_size=200, node_color=node_colors, edge_color='gray', alpha=0.6)

# 添加标签
labels = {node: node for node in G.nodes()}
label_pos = {node: (pos[node][0], pos[node][1] + 0.01) for node in G.nodes()}
nx.draw_networkx_labels(G, pos=label_pos, labels=labels, font_size=10, font_color='black', verticalalignment='bottom')

# 添加图例
legend_labels = ['Nodes with loop', 'Nodes without loop', 'Overlapping nodes']
legend_colors = ['green', 'red', 'blue']

# 创建一个透明的散点图用于图例
for color, label in zip(legend_colors, legend_labels):
    plt.scatter([], [], color=color, label=label)

plt.legend(loc='upper right')  # 可以根据需要调整位置

plt.subplot(1, 2, 2)

plt.axis('off')

wrapped_text = "\n".join([
    "\n".join(textwrap.wrap(f"{k}: {v}", width=70))
    for k, v in gene_labels.items()
])
plt.figtext(0.5, 0.25, wrapped_text, ha='left', fontsize=15)

plt.tight_layout()
plt.savefig('graph_res_4.png')
# plt.show()