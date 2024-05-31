from _core.construct_ddg import c_ddg, c_ast

MAX_LINE_GAP = 20
class Dep:
    def __init__(self, oss_name, commit, patch_info, taint_dict):
        self.oss_name = oss_name
        self.commit = commit
        self.patch_info = patch_info
        self.taint_dict = taint_dict
        self.ddg_nodes, self.ddg_edges = c_ddg(f'json/{oss_name}/{commit}/ddg.json')
        self.ast_nodes = c_ast(f'json/{oss_name}/{commit}/ast.json')
        #self.ast_nodes = c_ast(f'json/{oss_name}/{commit}/ast.json')

        line_node_dict = dict()
        self.line_node_dict = self.line_to_nodes(line_node_dict, self.ast_nodes)

        self.source_variable_linenum = list()
        self.vul_variable = list()
        self.taint_list = list()

        self.vul_lineno_list = list()


        self.get_source_variable(self.patch_info)
        if "NULL" in self.vul_variable:
            self.vul_variable.remove("NULL")
        self.vul_variable = list(set(self.vul_variable))
        self.get_taint_start()

        self.taint_list_bak = self.taint_list
        self.traversal()

        # sort the vul_lineno_list and delete the add patch line
        add_line_list = [int(line) for line in self.patch_info._add_lines]
        self.vul_lineno_list = sorted([x for x in self.vul_lineno_list if x not in add_line_list], reverse=False)

        print("vul list:", self.vul_lineno_list)



    def line_to_nodes(self, line_node_dict, nodes):
        for node in nodes.keys():
            lineno = nodes[node].node_lineno
            if lineno not in line_node_dict.keys():
                line_node_dict[lineno] = list()
                line_node_dict[lineno].append(node)
            else:
                if node not in line_node_dict[lineno]:
                    line_node_dict[lineno].append(node)

        return line_node_dict

    def get_source_variable(self, res):
        '''get the source: patch variable type: IDENTIFIER or pointer'''
        if len(res._add_lines) > 0:
            for line_num in res._add_lines:
                uncommon_string = self.taint_dict[res._file_name][line_num]
                if int(line_num) not in self.line_node_dict:
                    continue
                source_node_ids = self.line_node_dict[int(line_num)]
                source_nodes = list()
                for node_id in source_node_ids:
                    source_nodes.append(self.ast_nodes[node_id])
                    node = self.ast_nodes[node_id]

                    if node.node_type == 'IDENTIFIER' or \
                            node.node_type == '<operator>.indirectFieldAccess' or \
                            node.node_type == '<operator>.fieldAccess':
                        if uncommon_string == "":
                            #print(node.__str__())
                            self.source_variable_linenum.append(node.node_lineno)
                            self.vul_variable.append(node.node_content)
                        elif node.node_content in uncommon_string:
                            #print(node.__str__())
                            self.source_variable_linenum.append(node.node_lineno)
                            self.vul_variable.append(node.node_content)

    def get_taint_start(self):
        for node_id in self.ast_nodes.keys():
            if self.ast_nodes[node_id].node_lineno in self.source_variable_linenum:
                self.taint_list.append(node_id)


    def check_node(self, node):
        '''check the out node is assignment statement or call statement'''
        if '<operator>.assignment' in node.node_type:
            return True
        #if '<operator>.' in node.node_type or node.node_type in other_type_list:
            #return False

        return False

    def traversal(self):
        if len(self.taint_list) == 0:
            return
        ana_id = self.taint_list.pop(0)
        for edge in self.ddg_edges:
            if edge.in_edge_id == ana_id:
                in_node, out_node = self.ast_nodes[edge.in_edge_id], self.ast_nodes[edge.out_edge_id]

                if self.commit == '2d453188c2303da641dafb048dc1806790526dfd' or \
                        self.commit == '347cb14b7cba7560e53f4434b419b9d8800253e7':
                    MAX_LINE_GAP = 30
                else:
                    MAX_LINE_GAP = 20

                if out_node.node_lineno < in_node.node_lineno or \
                        out_node.node_lineno - max(self.source_variable_linenum) > MAX_LINE_GAP:
                    continue

                print(edge.in_edge_id, '->', edge.out_edge_id, edge.edge_label)
                if edge.edge_label.startswith('&amp;'):
                    edge.edge_label = edge.edge_label[5:]
                print(edge.out_edge_id, self.ast_nodes[edge.out_edge_id].node_lineno,
                      self.ast_nodes[edge.out_edge_id].node_content)

                if edge.edge_label in self.vul_variable:
                    if edge.out_edge_id not in self.taint_list_bak:
                        self.taint_list.append(edge.out_edge_id)
                        self.taint_list_bak.append(edge.out_edge_id)
                    if self.ast_nodes[edge.out_edge_id].node_lineno not in self.vul_lineno_list:
                        # append line into list
                        self.vul_lineno_list.append(self.ast_nodes[edge.out_edge_id].node_lineno)

                if self.check_node(out_node):
                    # get the variable that be assigned
                    # a = MIN(b, c) split left and right through '='
                    left, right = out_node.node_content.split('=')[0], out_node.node_content.split('=')[1]
                    node_ids = self.line_node_dict[out_node.node_lineno]

                    for node_id in node_ids:
                        node = self.ast_nodes[node_id]
                        if node.node_type == 'IDENTIFIER' and node.node_content != edge.edge_label and node.node_content in left:
                            if node.node_content not in self.vul_variable:
                                self.vul_variable.append(node.node_content)
                            if node.node_lineno not in self.vul_lineno_list:
                                # append line into list
                                self.vul_lineno_list.append(node.node_lineno)

        self.taint_list = sorted(self.taint_list)
        if len(self.taint_list) > 0:
            self.traversal()


