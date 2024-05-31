import Levenshtein

from _core.utils import Node
import string



class Distance():
    def __init__(self, tree):
        self.tree = tree
        self.prefix_list = list()

    def node_expression(self, node: Node):
        if node.kind and node.content:
            return node.kind + '/' + node.content
        else:
            return node.kind

    def tree_to_prefix_expression(self, node: Node):
        if node is None:
            return list()

        # 递归地获取子树的前缀表达式
        children_expressions = list()
        if len(node.children) > 0:
            for i, child in enumerate(node.children):
                child_expression = self.tree_to_prefix_expression(child)
                children_expressions = children_expressions + child_expression

        return_list = [self.node_expression(node)] + children_expressions
        return return_list


def levenshtein_ratio(list1, list2):
    letters = list(string.ascii_lowercase + string.ascii_uppercase + string.digits)
    word_letter_dict = dict()
    str1, str2 = str(), str()
    for i in list1:
        if i not in word_letter_dict.keys():
            word_letter_dict[i] = letters.pop(0)
        str1 += word_letter_dict[i]

    for j in list2:
        if j not in word_letter_dict.keys():
            word_letter_dict[j] = letters.pop(0)
        str2 += word_letter_dict[j]
    print(str1, str2)

    return Levenshtein.ratio(str1, str2)
