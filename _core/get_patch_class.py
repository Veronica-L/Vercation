import os.path
import re
import shutil, subprocess
from git import Repo
from _core.utils import rm_comments, compute_line_ratio, longest_common_substring
from _core.git_commit_class import Commit_Diff_Segment

def is_source_code_file(filename):
    # make sure the target patch is from source code file.
    # return True if filename is a source code file
    return filename.endswith('.c') or filename.endswith('.cpp') \
           or filename.endswith('.cxx')

class CommonCommit:
    def __init__(self, repository_path, oss_name, commit, file, method_name):
        self.repository_path = repository_path
        self._repository = Repo(self.repository_path)
        self.oss_name = oss_name
        self.commit = commit
        self.file = file
        self.method_name = method_name

    def get_method_delete(self, lineno):
        commit_content = self._repository.git.show(f"{self.commit}")
        diff_head_pattern = f'diff --git a/{self.file}[\S\s]*'
        match_ress = re.finditer(diff_head_pattern, commit_content)
        match_ress = list(match_ress)
        for idx in range(len(match_ress)):
            change_infos = list()
            mr = match_ress[idx]
            patch_code_start = mr.span()[0]
            if idx == len(match_ress) - 1:  # the last one
                patch_code_end = len(commit_content)
            else:
                patch_code_end = match_ress[idx + 1].span()[0]

            integer_pattern = "(?P<{}>[0-9]+)"
            patch_code_content = commit_content[patch_code_start:patch_code_end]
            #防止patch_code_content不准
            if patch_code_content.count('diff --git') > 1:
                first_index = patch_code_content.index('diff --git')
                second_index = patch_code_content.index('diff --git', first_index + 1)
                patch_code_content = patch_code_content[:second_index]

            #function_header_pattern = \
                #"@@ -{},{} \+{},{} @@ (\S*?[\s]*)(?P<return_type>\S*?)[\s]*(?P<func_name>\S+)[\s]*\(.*?\)?.*?\n"
            function_header_pattern = "@@ -{},{} \+{},{} @@.*\n"
            function_header_pattern = \
                function_header_pattern.format(integer_pattern.format("a_start"), integer_pattern.format('a_lines'),
                                               integer_pattern.format("b_start"), integer_pattern.format("b_lines"))
            matched_functions = list(re.finditer(function_header_pattern, patch_code_content))
            ll = len(matched_functions)
            '''
            function_header_pattern = "@@ -{},{} \+{},{} @@\n"
            function_header_pattern = \
                function_header_pattern.format(integer_pattern.format("a_start"), integer_pattern.format('a_lines'),
                                           integer_pattern.format("b_start"), integer_pattern.format("b_lines"))
            matched_functions = list(re.finditer(function_header_pattern, patch_code_content))
            ll = len(matched_functions)'''
            for idx in range(ll):
                mf = matched_functions[idx]
                matched_dict = mf.groupdict()
                a_start, a_lines, b_start, b_lines = matched_dict['a_start'], matched_dict['a_lines'], matched_dict[
                    'b_start'], matched_dict['b_lines']
                if lineno >= int(b_start) and lineno < int(b_start) + int(b_lines):
                    if idx == ll - 1:
                        code_end_pos = len(patch_code_content)
                    else:
                        code_end_pos = matched_functions[idx + 1].span()[0]
                    code_start_pos = mf.span()[1]
                    source_code = patch_code_content[code_start_pos:code_end_pos]
                    #source_code = rm_comments(source_code)

                    old_index, new_index = 0, 0
                    delete_lines, add_lines = list(), list()

                    p_mark = 'empty'
                    for line in source_code.split('\n'):
                        if line.startswith('-'):
                            if p_mark == 'empty':
                                delete_lines = list()
                                delete_lines.append(int(a_start) + old_index)
                            elif p_mark == '+':
                                delete_lines = list()
                                delete_lines.append(int(a_start) + old_index)
                            elif p_mark == '-':
                                delete_lines.append(int(a_start) + old_index)
                            old_index += 1
                            p_mark = '-'
                        elif line.startswith('+'):
                            if p_mark == 'empty':
                                add_lines = list()
                                add_lines.append(int(b_start) + new_index)
                            elif p_mark == '-':
                                add_lines = list()
                                add_lines.append(int(b_start) + new_index)
                            elif p_mark == '+':
                                add_lines.append(int(b_start) + new_index)
                            new_index += 1
                            p_mark = '+'
                        else:
                            if p_mark == '-' or p_mark == '+':
                                change_info_dict = {"del_lines": delete_lines, "add_lines": add_lines}
                                change_infos.append(change_info_dict)
                                delete_lines, add_lines = list(), list()
                            old_index += 1
                            new_index += 1
                            p_mark = 'empty'

            '''
            else:
                for idx in range(ll):
                    mf = matched_functions[idx]
                    matched_dict = mf.groupdict()
                    func_name = mf.groupdict()['func_name']

                    a_start, a_lines, b_start, b_lines = matched_dict['a_start'], matched_dict['a_lines'], matched_dict[
                        'b_start'], matched_dict['b_lines']
                    if idx == ll - 1:
                        code_end_pos = len(patch_code_content)
                    else:
                        code_end_pos = matched_functions[idx + 1].span()[0]
                    code_start_pos = mf.span()[1]
                    source_code = patch_code_content[code_start_pos:code_end_pos]
                    #source_code = rm_comments(source_code)

                    if f"void {self.method_name}" not in source_code and\
                            f"int {self.method_name}" not in source_code and\
                            func_name != self.method_name:
                        continue

                    old_index, new_index = 0, 0
                    delete_lines, add_lines = list(), list()

                    p_mark = 'empty'
                    for line in source_code.split('\n'):
                        if line.startswith('-'):
                            if p_mark == 'empty':
                                delete_lines = list()
                                delete_lines.append(int(a_start) + old_index)
                            elif p_mark == '+':
                                delete_lines = list()
                                delete_lines.append(int(a_start) + old_index)
                            elif p_mark == '-':
                                delete_lines.append(int(a_start) + old_index)
                            old_index += 1
                            p_mark = '-'
                        elif line.startswith('+'):
                            if p_mark == 'empty':
                                add_lines = list()
                                add_lines.append(int(b_start) + new_index)
                            elif p_mark == '-':
                                add_lines = list()
                                add_lines.append(int(b_start) + new_index)
                            elif p_mark == '+':
                                add_lines.append(int(b_start) + new_index)
                            new_index += 1
                            p_mark = '+'
                        else:
                            if p_mark == '-' or p_mark == '+':
                                change_info_dict = {"del_lines": delete_lines, "add_lines": add_lines}
                                change_infos.append(change_info_dict)
                                delete_lines, add_lines = list(), list()
                            old_index += 1
                            new_index += 1
                            p_mark = 'empty'
                            '''

        return change_infos


class patchCommit:
    def __init__(self, repository_path, oss_name, patch_commit, file, patch_index):
        self.repository_path = repository_path
        self._repository = Repo(self.repository_path)
        self.oss_name = oss_name
        self.patch_commit = patch_commit
        self.file = file
        self.patch_index = patch_index
        self.add_lines = dict() #line_num: code
        self.delete_lines = dict() #line_num: code


    def retrieve_commit_content(self):
        commit_content = self._repository.git.show(f"{self.patch_commit}")

        diff_head_pattern = 'diff --git a/(?P<filename>[\S]+)'
        match_ress = re.finditer(diff_head_pattern, commit_content)
        match_ress = list(match_ress)
        return_res = {}
        for idx in range(len(match_ress)):
            mr = match_ress[idx]
            filename = mr.groupdict()['filename']
            if filename != self.file:
                continue
            if not is_source_code_file(filename):
                continue

            return_res[filename] = []
            patch_code_start = mr.span()[0]
            if idx == len(match_ress) - 1:  # the last one
                patch_code_end = len(commit_content)
            else:
                patch_code_end = match_ress[idx + 1].span()[0]

            patch_code_content = commit_content[patch_code_start:patch_code_end]
            integer_pattern = "(?P<{}>[0-9]+)"
            function_header_pattern = \
                "@@ -{},{} \+{},{} @@ (\S*?[\s]*)(?P<return_type>\S*?)[\s]*(?P<func_name>\S+)[\s]*\(.*?\)?.*?\n"
            function_header_pattern = \
                function_header_pattern.format(integer_pattern.format("a_start"), integer_pattern.format('a_lines'),
                                               integer_pattern.format("b_start"), integer_pattern.format("b_lines"))
            matched_functions = list(re.finditer(function_header_pattern, patch_code_content))
            ll = len(matched_functions)
            code_line_map_patch = self.code_line_map(self.patch_commit)
            previous_hexsha = self._repository.commit(self.patch_commit).parents[0].hexsha
            code_line_map_unpatch = self.code_line_map(previous_hexsha)

            for idx in range(ll):
                if idx != self.patch_index: continue
                func = matched_functions[idx]
                matched_dict = func.groupdict()
                matched_dict["file_name"] = filename
                a_start, a_lines, b_start, b_lines = matched_dict['a_start'], matched_dict['a_lines'], matched_dict['b_start'], matched_dict['b_lines']

                diff_lines = (int(b_start) + int(b_lines)) - (int(a_start) + int(a_lines))
                matched_dict['diff_lines'] = diff_lines

                if idx == ll - 1:
                    code_end_pos = len(patch_code_content)
                else:
                    code_end_pos = matched_functions[idx + 1].span()[0]
                code_start_pos = func.span()[1]
                source_code = patch_code_content[code_start_pos:code_end_pos]
                #matched_dict['source_code'] = rm_comments(source_code)
                matched_dict['source_code'] = source_code
                matched_dict['code_line_map_patch'] = code_line_map_patch
                matched_dict['code_line_map_unpatch'] = code_line_map_unpatch
                cds = Commit_Diff_Segment(**matched_dict)
                self.get_diff_lines(cds)
                return_res[filename].append(cds)
        return return_res, code_line_map_unpatch

    def get_diff_lines(self, cds: Commit_Diff_Segment):
        # get add/delete lines dict
        vul_index, patch_index = 0, 0
        for line in cds._source_code.split('\n'):
            if line.startswith('-'):
                cds._delete_lines[str(int(cds._a_start) + vul_index)] = line[1:].strip()
                vul_index += 1
            elif line.startswith('+'):
                cds._add_lines[str(int(cds._b_start) + patch_index)] = line[1:].strip()
                patch_index += 1
            else:
                vul_index += 1
                patch_index += 1

    def code_line_map(self, commit):
        code_line_map = dict()
        lineno = 0
        if not os.path.exists(f"source/{self.oss_name}/{commit}/{self.file}"):
            src = f"source/{self.oss_name}/{self.oss_name}"
            dst = f"source/{self.oss_name}/{commit}"
            shutil.copytree(src, dst)
            os.chdir(dst)
            subprocess.run(['git', 'checkout', commit])
            os.chdir('../../../')

        with open(f"source/{self.oss_name}/{commit}/{self.file}", 'r', encoding='utf-8')  as f:
            lines = f.readlines()
        for line in lines:
            lineno += 1
            code_line_map[lineno] = line.strip()
        return code_line_map

        '''        
        commit = self._repository.commit(self.patch_commit)
        tree = commit.tree

        code_line_map = dict()
        lineno = 0
        with open(tree[self.file].abspath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            lineno += 1
            code_line_map[lineno] = line.strip()
        return code_line_map '''



def diff_prune(commit_content):
    taint_dict = dict()
    for changed_file in commit_content:
        cds_lists = commit_content[changed_file]
        taint_line_dict = dict()
        for cds in cds_lists:
            max_ratio = 0
            add_lines_dict, delete_lines_dict = cds._add_lines, cds._delete_lines
            if len(add_lines_dict) != 0 and len(delete_lines_dict) != 0:
                '''add && delete'''
                for add_line in add_lines_dict:
                    for delete_line in delete_lines_dict:
                        ratio = compute_line_ratio(add_lines_dict[add_line], delete_lines_dict[delete_line])
                        if ratio >= max_ratio:
                            max_ratio = ratio
                            most_similar_delete_linenum = delete_line
                    if len(add_lines_dict[add_line]) > len(delete_lines_dict[most_similar_delete_linenum]) and\
                        delete_lines_dict[most_similar_delete_linenum] in add_lines_dict[add_line]:
                        common_string = longest_common_substring(add_lines_dict[add_line], delete_lines_dict[most_similar_delete_linenum])
                        uncommon_string = add_lines_dict[add_line].replace(common_string, '')
                    else:
                        uncommon_string = ''
                    print('add line:', add_line, 'delete line:', most_similar_delete_linenum, ratio, uncommon_string)
                    taint_line_dict[add_line] = uncommon_string
            elif len(add_lines_dict) == 0:
                '''only delete'''
                for delete_line in delete_lines_dict:
                    taint_line_dict[delete_line] = delete_lines_dict[delete_line]
            elif len(delete_lines_dict) == 0:
                '''only add'''
                for add_line in add_lines_dict:
                    taint_line_dict[add_line] = add_lines_dict[add_line]

        taint_dict[changed_file] = taint_line_dict
        return taint_dict


if __name__ == '__main__':
    oss_name = 'ffmpeg'
    #patch_commit = 'ed38046c5c2e3b310980be32287179895c83e0d8'
    patch_commit = 'ba4beaf6149f7241c8bd85fe853318c2f6837ad0'
    p = patchCommit(repository_path=f'source/{oss_name}/test', oss_name=oss_name, patch_commit=patch_commit)
    return_res = p.retrieve_commit_content()
    taint_dict = diff_prune(return_res)


