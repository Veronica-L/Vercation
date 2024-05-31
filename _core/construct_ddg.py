# -*- coding: utf-8 -*-
import json
import os, re

def get_dot(dotfile):
    graph = nx.drawing.nx_agraph.read_dot(dotfile)
    print(graph)

def dot_traversal(path):
    # 遍历目录及子目录下的所有文件
    for root, dirs, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(path, filename)

            get_dot(filepath)

class DdgNode:
    def __init__(self, match, pre_match, file_contents):
        self.node_type = None
        self.node_lineno = 0
        self.node_id = None
        self.node_content = None

        self.construct_node(match=match, pre_match=pre_match, file_contents=file_contents)

    def construct_node(self, match, pre_match, file_contents):
        pre_regs = pre_match.regs
        self.node_id = file_contents[pre_regs[0][0] + 4:pre_regs[0][1] - 2]
        pre_label = file_contents[pre_regs[0][1] + 1:match.regs[0][0]]

        p1 = re.compile(r'[(](.*?)[)]', re.S)  # 取括号内内容
        p2 = re.compile(r'(?<=<SUB>).*(?=</SUB>)', re.S)  # 取SUB内内容
        label_content = re.findall(p1, pre_label)
        self.node_type, self.node_content = label_content[0].split(',')[0], label_content[0].split(',')[1]
        self.node_lineno = int(re.findall(p2, pre_label)[0])
        self.node_type = self.node_type.replace('&lt;','<').replace('&gt;','>')
        self.node_content = self.node_content.replace('&lt;', '<').replace('&gt;', '>')


class DdgEdge:
    def __init__(self, match, pre_match, file_contents):
        self.in_edge_id = None
        self.out_edge_id = None
        self.edge_label = None

        self.construct_edge(match, pre_match, file_contents)

    def construct_edge(self, match, pre_match, file_contents):
        #print(match, pre_match)
        to_string = file_contents[pre_match.regs[0][0]:pre_match.regs[0][1]]
        self.in_edge_id = to_string[2:to_string.index('->')-3]
        self.out_edge_id = to_string[to_string.index('->')+5:-2]

        self.edge_label = file_contents[pre_match.regs[0][1]+14: match.regs[0][0]-8]
        self.edge_label = self.edge_label.replace('&lt;', '<').replace('&gt;', '>')

class AstNode:
    def __init__(self, match, pre_match, file_contents):
        self.node_type = None
        self.node_lineno = 0
        self.node_id = None
        self.node_content = None

        self.construct_node(match=match, pre_match=pre_match, file_contents=file_contents)

    def __str__(self):
        return "".join([self.node_type, ',', str(self.node_lineno), ',', self.node_id, ',', self.node_content])

    def construct_node(self, match, pre_match, file_contents):
        pre_regs = pre_match.regs
        self.node_id = file_contents[pre_regs[0][0] + 4:pre_regs[0][1] - 2]
        #print(self.node_id)
        pre_label = file_contents[pre_regs[0][1] + 1:match.regs[0][0]]
        if pre_label == "":
            return

        p1 = re.compile(r'[(](.*?)[)]', re.S)  # 取括号内内容\
        p = re.compile(r'(?<=label = <\().*(?=\)<SUB>)', re.S)
        p2 = re.compile(r'(?<=<SUB>).*(?=</SUB>)', re.S)  # 取SUB内内容

        label_content = re.findall(p, pre_label)[0]
        self.node_type = label_content[:label_content.index(',')]
        if self.node_type != 'IDENTIFIER' and self.node_type != 'CONTROL_STRUCTURE':
            self.node_content = label_content[label_content.index(',')+1:]
        else:
            part_two = label_content[label_content.index(',')+1:]
            self.node_content = part_two[:part_two.index(',')]
        self.node_lineno = int(re.findall(p2, pre_label)[0])
        self.node_type = self.node_type.replace('&lt;','<').replace('&gt;','>').replace('&quot;', '"')
        self.node_content = self.node_content.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')


def c_ddg(json_fp):
    with open(json_fp) as json_file:
        file_contents = json_file.read()

    pattern = r'\\n\\"\d{1,9}\\"'
    pre_match = None
    id_label_dict = {}
    # node
    for match in re.finditer(pattern, file_contents):
        #print(match.group())
        if pre_match == None:
            pre_match = match
            continue
        else:
            node = DdgNode(match, pre_match, file_contents)
            id_label_dict[node.node_id] = node
            pre_match = match

    # edge
    pre_m = None
    pattern_edge = r'\\"\d{1,9}\\" -> \\"\d{1,9}\\"'
    edge_list = []
    for m in re.finditer(pattern_edge, file_contents):
        #print(m.group())
        if pre_m == None:
            pre_m = m
            continue
        else:
            edge = DdgEdge(m, pre_m, file_contents)
            edge_list.append(edge)
            pre_m = m

    return id_label_dict, edge_list



def c_ast(json_fp):
    with open(json_fp) as json_file:
        file_contents = json_file.read()

    pattern = r'\\n\\"\d{1,9}\\"'
    pre_match = None
    id_label_dict = {}
    # node
    for match in re.finditer(pattern, file_contents):
        #print(match.group())
        if pre_match == None:
            pre_match = match
            continue
        else:
            node = AstNode(match, pre_match, file_contents)
            id_label_dict[node.node_id] = node
            pre_match = match

    #last node
    pattern_edge = r'\\n\ \ \\"\d{1,9}\\" -> \\"\d{1,9}\\"'
    edge_start_match = re.search(pattern_edge, file_contents)
    node = AstNode(edge_start_match, match, file_contents)
    id_label_dict[node.node_id] = node

    return id_label_dict

if __name__ == '__main__':
    id_label_dict, edge_list = c_ddg('../json/wget-1.19.2/test.json')
