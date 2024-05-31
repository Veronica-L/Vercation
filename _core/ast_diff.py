import json
import re
import os
from _core.utils import Node
from _core.ast_compare import Distance, levenshtein_ratio

def del_id():
    f = open('source/ffmpeg/previous.json')
    new_f = open('source/ffmpeg/next_new.json', 'w')
    lines = f.readlines()
    for line in lines:
        pattern = re.compile(r':\ \"0x[a-zA-Z0-9]*\"')
        # print(pattern.findall(line))

        new_line = re.sub(pattern, ': "0x0"', line)
        print(new_line)
        new_f.write(new_line)

def ConvertToDict(file):
    with open(file) as f:
        file_dict = json.load(f)
    return file_dict

def diff_file():
    previous_dict = ConvertToDict('source/ffmpeg/previous_new.json')
    next_dict = ConvertToDict('source/ffmpeg/next_new.json')
    diff_content = json_tools.diff(previous_dict, next_dict)
    with open(os.path.join("../source/ffmpeg", "cmp{}.json".format(1)), "w", encoding='utf-8') as f:
        json.dump(diff_content, f, ensure_ascii=False, indent=4)

class Solution():
    def __init__(self, vul_file, line):
        self.stop_flag = False
        self.previous_dict = dict()
        self.target_dict = dict()
        self.line = line
        self.vul_file = vul_file


    def iterate_dict(self, dictionary):
        '''
        find the line range in ast
        get self.target_dict
        '''
        for key, value in dictionary.items():
            if key == 'id':
                self.previous_dict = dictionary
            if self.stop_flag == True:
                return
            if key == 'line' and value == self.line:
                if 'file' in dictionary and ( dictionary['file'] == self.vul_file\
                        or dictionary['file'] == self.vul_file[self.vul_file.index('/')+1:]):
                    self.stop_flag = True
                    print(self.previous_dict)
                    self.target_dict = self.previous_dict
                    break
                elif 'file' not in dictionary and 'includedFrom' not in dictionary:
                    self.stop_flag = True
                    print(self.previous_dict)
                    self.target_dict = self.previous_dict
                    break
            if key == "expansionLoc" and 'file' in dictionary["expansionLoc"] and \
                dictionary["expansionLoc"]["file"] == self.vul_file and \
                dictionary["expansionLoc"]["line"] == self.line:
                self.stop_flag = True
                print(self.previous_dict)
                self.target_dict = self.previous_dict
                break

            if isinstance(value, dict):
                self.iterate_dict(value)
            elif isinstance(value, list):
                for son_dict in value:
                    if isinstance(son_dict, dict):
                        self.iterate_dict(son_dict)
                    else:
                        print(son_dict)


        if self.stop_flag == True:
            return

key_list = ['kind', 'opcode', 'name', 'inner', 'referencedDecl']

def ConvertToTree(dictionary):
    '''将ast的dictionary形式转换为树'''
    node = Node()
    for key, value in dictionary.items():
        if key == 'kind':
            node.kind = value
        elif key == 'opcode' or key == 'name':
            node.content = value
        elif isinstance(value, list):
            for son_dict in value:
                c1 = ConvertToTree(son_dict)
                if c1.kind != None or c1.content != None or c1.children != []:
                    node.children.append(c1)
        elif isinstance(value, dict):
            c2 = ConvertToTree(value)
            if c2.kind != None or c2.content != None or c2.children != []:
                node.children.append(c2)

    return node

delete_kinds = ['ImplicitCastExpr', 'ParenExpr']
def TreeDelete(tree: Node):
    '''删除不必要的节点如ImplicitCastExpr, ParenExpr'''
    for i, c in enumerate(tree.children):
        if c.kind == 'ImplicitCastExpr' or c.kind == 'ParenExpr':
            c_childrens = c.children
            tree.children.pop(i)
            if len(c_childrens) > 0:
                tree.children[i:i] = c_childrens
            TreeDelete(tree)
        else:
            TreeDelete(c)

    return tree


def TreeEqualConvert1(treenode: Node):
    for tn in treenode.children:
        '''
        a > b - c normalize to a + c > b
        '''
        if tn.content == '>' or tn.content == '<':
            for index, child in enumerate(tn.children):
                if child.content == '-':
                    another_index = 1 if index == 0 else 0
                    c_left = child.children[0] #b
                    c_right = child.children[1] #c

                    add_node = Node()
                    add_node.kind = 'BinaryOperator'
                    add_node.content = '+'
                    add_node.children.append(tn.children[another_index])
                    add_node.children.append(c_right)

                    tn.children[another_index] = add_node
                    tn.children[index] = c_left
            continue
        if tn.children:
            TreeEqualConvert1(tn)

    return treenode

def TreeEqualConvert2(treenode: Node):
    '''处理三元运算符'''
    if treenode.content == '=':
        for i, child in enumerate(treenode.children):
            if child.kind == 'ConditionalOperator':
                another_index = 1 if i == 0 else 0
                be_assigned_node = treenode.children[another_index]
                conditionTrue, conditionFalse, v = child.children[0], child.children[1], child.children[2]

                child.kind = 'IfStmt'
                add_node = Node()
                add_node.kind, add_node.content = 'BinaryOperator', '='
                add_node.children = [be_assigned_node, conditionFalse]
                child.children[1] = add_node

                return child

    return treenode



def print_tree(node, indent=""):
    if isinstance(node, list):
        for n in node:
            print_tree(n, indent + "--")
    else:
        if node.kind and node.content:
            print(indent + 'kind:' + node.kind + '\n' + indent + 'value:' + node.content)
        elif node.kind:
            print(indent + 'kind:' + node.kind)
        elif node.content:
            print(indent + 'kind:' + node.content)
        else:
            print(indent + "None")
        for child in node.children:
            print_tree(child, indent + "--")

def get_tree_prefix(file_path, vul_file, line):
    s = Solution(vul_file, line)
    s.iterate_dict(ConvertToDict(file_path))
    tree = ConvertToTree(s.target_dict)
    #print_tree(tree)

    new_tree = TreeDelete(tree=tree)
    if new_tree.kind in delete_kinds:
        new_tree = new_tree.children[0]
    #print_tree(new_tree)

    new_tree2 = TreeEqualConvert1(treenode=new_tree)
    new_tree2 = TreeEqualConvert2(treenode=new_tree2)
    #print_tree(new_tree2)

    expression = Distance(new_tree2)
    return_list = expression.tree_to_prefix_expression(new_tree2)
    #print(return_list)

    return return_list

if __name__ == "__main__":
    #del_id()
    #diff_file()
    #next_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2016-7122/next.json', 'libavformat/avidec.c', 353)
    #previous_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2016-7122/previous.json', 'libavformat/avidec.c', 353)

    #next_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2014-8543/next.json', 'libavcodec/mmvideo.c', 112)
    #previous_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2014-8543/previous.json', 'libavcodec/mmvideo.c', 110)
    #next_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2017-14767/next.json', 'libavformat/rtpdec_h264.c', 171)
    #previous_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2017-14767/previous.json', 'libavformat/rtpdec_h264.c', 171)
    next_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2017-7862/next.json', 'libavcodec/pictordec.c', 153)
    previous_tree_prefix = get_tree_prefix('source/ffmpeg/CVE-2017-7862/previous.json', 'libavcodec/pictordec.c', 154)

    print(levenshtein_ratio(next_tree_prefix, previous_tree_prefix))






