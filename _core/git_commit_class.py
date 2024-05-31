from git import Repo
from _core.construct_ddg import c_ddg, c_ast
from _core.type import black_variable_list

def line_to_nodes(line_node_dict, nodes):
    for node in nodes.keys():
        lineno = nodes[node].node_lineno
        if lineno not in line_node_dict.keys():
            line_node_dict[lineno] = list()
            line_node_dict[lineno].append(node)
        else:
            if node not in line_node_dict[lineno]:
                line_node_dict[lineno].append(node)

    return line_node_dict

class Commit_Diff_Segment():
    def __init__(self, func_name, a_start, a_lines, b_start, b_lines, file_name, return_type, diff_lines, source_code, code_line_map_patch, code_line_map_unpatch):
        self._func_name = func_name
        self._a_start = a_start
        self._a_lines = a_lines
        self._b_start = b_start
        self._b_lines = b_lines
        self._file_name = file_name
        self._return_type = return_type
        self._diff_lines = diff_lines
        self._source_code = source_code
        self._code_line_map_patch = code_line_map_patch
        self._code_line_map_unpatch = code_line_map_unpatch

        self._add_lines = dict()
        self._delete_lines = dict()


    def __str__(self):
        return "\n".join([self._file_name,
                          self._a_start + "," + self._a_lines + " " + self._b_start + "," + self._b_lines,
                          self._return_type + " " + self._func_name,
                          self._source_code])

    @property
    def source_code(self):
        return self._source_code


class PatchInfo(Commit_Diff_Segment):
    def __init__(self, repo, oss_name, oss_version, func_name, a_start, a_lines, b_start, b_lines, file_name, return_type, diff_lines, source_code):
        super(PatchInfo, self).__init__(func_name, a_start, a_lines, b_start, b_lines, file_name, return_type, diff_lines, source_code)
        self.repo = repo
        self.code_variable_map = dict()
        self.patch_type = None
        self.patch_cond = None
        self.get_code_variable_map(oss_name, oss_version)


    def get_code_variable_map(self, oss_name, oss_version):
        ddg_nodes, ddg_edge = c_ddg(f'json/{oss_name}/{oss_version}/ddg.json')
        ast_nodes = c_ast(f'json/{oss_name}/{oss_version}/ast.json')
        line_node_dict = dict()
        line_node_dict = line_to_nodes(line_node_dict, ddg_nodes)
        line_node_dict = line_to_nodes(line_node_dict, ast_nodes)

        lines = self._source_code.split('\n')
        delete_count = 0
        for i in range(len(lines)):
            if lines[i][0] == '-':
                delete_count += 1
                continue
            if lines[i][0] == '+':
                # patch line
                lineno = int(self._b_start) + i - delete_count
                patch_code = lines[i].strip('+').strip(' ')

                #sorted_node_content = [(n_id, compute_line_ratio(patch_code.strip(';'), ast_nodes[n_id].node_content)) for n_id in ast_nodes]
                #sorted_node_content = sorted(sorted_node_content, key=lambda x: x[1], reverse=True)
                #lineno = ast_nodes[sorted_node_content[0][0]].node_lineno
                self.code_variable_map[lineno] = dict()
                self.code_variable_map[lineno]['code'] = patch_code
                if self.code_variable_map[lineno]['code'] == '':
                    continue

                node_list = line_node_dict[lineno]
                node_list = sorted(node_list)
                for n_id in node_list:
                    if ast_nodes[n_id].node_type == 'IDENTIFIER' and ast_nodes[n_id].node_content not in black_variable_list:
                        self.code_variable_map[lineno]['variable'] = list()
                        self.code_variable_map[lineno]['variable'].append(ast_nodes[n_id].node_content)
                    if ast_nodes[n_id].node_type == 'CONTROL_STRUCTURE':
                        self.patch_type = 'cond_add'
                    if '<operator>' in ast_nodes[n_id].node_type and self.patch_type == 'cond_add':
                        if self.patch_cond == None:
                            self.patch_cond = ast_nodes[n_id].node_content
                        elif ast_nodes[n_id].node_content in self.patch_cond:
                            continue


def get_tag_for_commit(repo: Repo, commit_hash):
    commit = repo.commit(commit_hash)
    tags = repo.git.tag("--contains", commit_hash).split('\n')

    matching_tags = []
    for tag in repo.tags:
        if commit_hash in [commit.hexsha for commit in tag.commit.iter_items(repo, commit_hash)]:
             matching_tags.append(tag.name)

    return tags[0], matching_tags[0]

def get_prev_commit(repo: Repo, commit_hash):
    commit_log = repo.git.log('--pretty={"commit":"%h","author":"%an","summary":"%s","date":"%cd"}', max_count=50, date='format:%Y-%m-%d %H:%M')
    log_list = commit_log.split("\n")
    real_log_list = [eval(item) for item in log_list]

    return real_log_list[1]['commit']
