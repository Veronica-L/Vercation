import os.path
import sys, subprocess, shutil

from git.repo import Repo
from pydriller import GitRepository as PyDrillerGitRepo
from enum import Enum
from typing import List
from _core.get_patch_class import CommonCommit
from _core.utils import compute_line_ratio, vul_method_keyword, MAXSIZE, compare_file_sim
from _core.ast_diff import get_tree_prefix
from _core.ast_compare import levenshtein_ratio

class DetectLineMoved(Enum):
    """
    DetectLineMoved represents the -C param of git blame (https://git-scm.com/docs/git-blame#Documentation/git-blame.txt--Cltnumgt),
    which detect lines moved or copied from other files that were modified in the same commit. The default [<num>] param
    of alphanumeric characters to detect is used (i.e. 40).

    * SAME_COMMIT = -C
    * PARENT_COMMIT = -C -C
    * ANY_COMMIT = -C -C -C
    """
    SAME_COMMIT = 1
    PARENT_COMMIT = 2
    ANY_COMMIT = 3

class myCommit():
    def __init__(self, repository_path, oss_name, patch_info, vul_lineno_list, prompt):
        self.repository_path = repository_path
        self._repository = Repo(self.repository_path)
        self.oss_name = oss_name
        self.patch_info = patch_info
        self.changed_method = self.patch_info._func_name
        self.vul_lineno_list = vul_lineno_list
        self.line_weight_list, self.overall_score, self.vul_score, self.novul_score = \
            self.assign_line_weight(prompt)
        self.mod_map = dict()
        self.score_map = dict() #commit 对应score

        self.introduce_commit = list()

    def assign_line_weight(self, prompt):
        line_weight_list = list()
        overall_score = 0
        if prompt == 'p':
            code_line_map = self.patch_info._code_line_map_patch
        else:
            code_line_map = self.patch_info._code_line_map_unpatch

        kw_list, other_list = list(), list()
        for lineno in self.vul_lineno_list:
            line_weight = 0
            line_code = code_line_map[int(lineno)]
            for keyword in vul_method_keyword:
                if keyword in line_code:
                    #line_weight = 0.5
                    #overall_score += line_weight
                    kw_list.append((lineno, line_code))
                    break
            if line_weight == 0 and len(kw_list) == 0:
                #line_weight = 0.5/len(self.vul_lineno_list)
                #overall_score += line_weight
                other_list.append((lineno, line_code))

        kw_score, other_score, overall_score = \
            3/(3*len(kw_list)+len(other_list)),  1/(3*len(kw_list)+len(other_list)), 1

        for k in kw_list:
            line_weight_list.append((k[0], k[1], kw_score))
        for o in other_list:
            line_weight_list.append((o[0], o[1], other_score))

        #line_weight_list.append((lineno, line_code, line_weight))

        return line_weight_list, overall_score, kw_score, other_score

    def calculate_diff_score(self, commit_map, commit):
        score = 0
        vul_flag = False
        for line in commit_map[commit]:
            if len(commit_map[commit][line]) == 0:
                for t in self.mod_map[commit.hexsha]:
                    lineno, content = t[0], t[1]
                    if lineno == line:
                        for kw in vul_method_keyword:
                            if kw in content:
                                score += self.vul_score
                                vul_flag = True
                                break
                        if vul_flag == False:
                            score += self.novul_score
                '''
                for t in entry_map[commit]:
                    if t[1] == line:
                        new_line = t[0]

                for wt in weight_list:
                    if wt[0] == new_line:
                        score += wt[2]
                '''

        return score

    def get_method_line_range(self, commit_hash, file_path, method_name):
        code_line_map = dict()
        lineno = 0
        with open(f"source/{self.oss_name}/{commit_hash}/{file_path}", 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            lineno += 1
            code_line_map[lineno] = line.strip()
        return code_line_map

    def _parse_line_ranges(self):
        mod_line_ranges = list()
        range_start_flag = True
        for index, lineno in enumerate(self.vul_lineno_list):
            if range_start_flag:
                range_start = lineno
                range_start_flag = False

            if index == len(self.vul_lineno_list) - 1:
                range_end = lineno
                mod_line_ranges.append(f'{str(range_start)},{str(range_end)}')
                break

            if self.vul_lineno_list[index+1] == int(lineno) + 1:
                continue
            else:
                range_end = lineno
                mod_line_ranges.append(f'{str(range_start)},{str(range_end)}')
                range_start_flag = True

        return mod_line_ranges


    def map_modified_line(self, rev, entry, blame_file_path):
        blame_commit = PyDrillerGitRepo(self.repository_path).get_commit(entry.commit.hexsha)
        mod_files = [mod.new_path for mod in blame_commit.modifications]
        if blame_file_path not in mod_files:
            #TODO: compare the file similarity with mod files
            modFile_simList = [(mod_file,
                                compare_file_sim(
                                    f"source/{self.oss_name}/{entry.commit.hexsha}/{mod_file}",
                                    f"source/{self.oss_name}/{rev}/{blame_file_path}")
                                ) for mod_file in mod_files]
            sorted_modFile_simList = sorted(modFile_simList, key=lambda x: x[1], reverse=True)
            blame_file_path = sorted_modFile_simList[0][0]

        for mod in blame_commit.modifications:
            file_path = mod.new_path
            if file_path != blame_file_path:
                continue
            if not mod.old_path:
                return -1, blame_file_path

            #for method in mod.changed_methods:
                #if method.name == self.changed_method:
                    #range_tuple = range(method.start_line, method.end_line)

            add_line_list, delete_line_list = mod.diff_parsed["added"], mod.diff_parsed["deleted"]
            #maybe there are many add lines, we should select the add line which maps the entry.linenos
            #add_line_list = [l for l in add_line_list if l[0] in range_tuple]
            #TODO: 获得add_line对应的 delete_line部分
            cc = CommonCommit(self.repository_path, self.oss_name, blame_commit.hash, blame_file_path, self.changed_method)

            #delete_line_list = [l for l in delete_line_list if l[0] in method_delete_lines]

            orig_lineno_range = entry.orig_linenos
            new_lineno_range = entry.linenos

            same_line_map = dict()
            for lineno in orig_lineno_range:

                add_code_list = [add_tuple for add_tuple in add_line_list if lineno == add_tuple[0]]

                method_delete_lines = cc.get_method_delete(lineno)
                for info_dict in method_delete_lines:
                    if lineno in info_dict['add_lines']:
                        del_lines = info_dict['del_lines']
                delete_line_list = [l for l in delete_line_list if l[0] in del_lines]

                # find the code from delete_line_list
                code, lineno = add_code_list[0][1].strip(), add_code_list[0][0]
                if code == '': continue
                if blame_commit.hash not in self.mod_map:
                    self.mod_map[blame_commit.hash] = list()
                self.mod_map[blame_commit.hash].append((lineno, code))
                sorted_lines_deleted = [(delete_tuple[0], delete_tuple[1],
                                             compute_line_ratio(code, delete_tuple[1].strip()),
                                             abs(lineno - delete_tuple[0]))
                                            for delete_tuple in delete_line_list]
                sorted_lines_deleted = sorted(sorted_lines_deleted, key=lambda x: (x[2], MAXSIZE - x[3]), reverse=True)
                if len(sorted_lines_deleted) == 0:
                    same_line_map[lineno] = []
                    continue

                # print(sorted_lines_deleted)
                if sorted_lines_deleted[0][2] > 0.88: #find the same code
                    same_line_map[lineno] = [sorted_lines_deleted[0][0]]
                else:
                    #TODO: AST Compare
                    #the tree prefix after commit
                    try:
                        next_ast_path = f'source/{self.oss_name}/{entry.commit.hexsha}/next.json'
                        if not os.path.exists(next_ast_path):
                            ll_file = blame_file_path.replace('.c', '.ll')
                            os.chdir(f'source/{self.oss_name}/{entry.commit.hexsha}')
                            subprocess.run(['clang -I./include -emit-llvm -gdwarf-4 -c -Xclang -ast-dump=json -fsyntax-only  -o', f'{ll_file}', blame_file_path, '> next.json'], capture_output=True, text=True)
                            os.chdir('../../../')

                        next_tree_prefix = get_tree_prefix(f'source/{self.oss_name}/{entry.commit.hexsha}/next.json', file_path, lineno)
                    except IndexError as e:
                        next_tree_prefix = [None]
                    print(next_tree_prefix)

                    #the tree prefix before commit
                    previous_tree_prefix_list = list()
                    for delete_line_tuple in delete_line_list:
                        previous_ast_path = f'source/{self.oss_name}/{entry.commit.hexsha}/previous.json'
                        if not os.path.exists(previous_ast_path):
                            os.chdir(f'source/{self.oss_name}/{entry.commit.hexsha}')
                            result = subprocess.run(["git", "log", "-2", "--pretty=format:%H"], capture_output=True,text=True)
                            previous_commit_hash = result.stdout.split('\n')[1].strip()
                            os.chdir('../../../')

                            if not os.path.exists(f'source/{self.oss_name}/{previous_commit_hash}'):
                                shutil.copytree(f'source/{self.oss_name}/{entry.commit.hexsha}', f'source/{self.oss_name}/{previous_commit_hash}')
                                os.chdir(f'source/{self.oss_name}/{previous_commit_hash}')
                                subprocess.run(['git', 'checkout', previous_commit_hash], capture_output=True, text=True)
                                os.chdir('../../../')

                            subprocess.run(
                                ['clang -I./include -emit-llvm -gdwarf-4 -c -Xclang -ast-dump=json -fsyntax-only  -o', f'{ll_file}', blame_file_path, f'> ../{entry.commit.hexsha}/previous.json'], capture_output=True, text=True)
                            os.chdir('../../../')

                        previous_tree_prefix = get_tree_prefix(f'source/{self.oss_name}/{entry.commit.hexsha}/previous.json', file_path, delete_line_tuple[0])
                        previous_tree_prefix_list.append(
                            (delete_line_tuple[0], delete_line_tuple[1].strip(),
                            levenshtein_ratio(previous_tree_prefix, next_tree_prefix))
                        )

                    previous_tree_prefix_list = sorted(previous_tree_prefix_list, key=lambda x: x[2], reverse=True)
                    same_line_map[lineno] = [t[0] for t in previous_tree_prefix_list if t[2] >= 0.8]
                    if next_tree_prefix == [None]:
                        same_line_map[lineno] = []

            return same_line_map, blame_file_path


    def blame(self, rev, file_path, ignore_revs_list: List[str] = None,
               ignore_revs_file_path: str = None,
               ignore_whitespaces: bool = False,
               detect_move_within_file: bool = False,
               detect_move_from_other_files: 'DetectLineMoved' = None):
        kwargs = dict()
        if ignore_whitespaces:
            kwargs['w'] = True
        if ignore_revs_file_path:
            kwargs['ignore-revs-file'] = ignore_revs_file_path
        if ignore_revs_list:
            kwargs['ignore-rev'] = list(ignore_revs_list)
        if detect_move_within_file:
            kwargs['M'] = True
        if detect_move_from_other_files and detect_move_from_other_files == DetectLineMoved.SAME_COMMIT:
            kwargs['C'] = True
        if detect_move_from_other_files and detect_move_from_other_files == DetectLineMoved.PARENT_COMMIT:
            kwargs['C'] = [True, True]
        if detect_move_from_other_files and detect_move_from_other_files == DetectLineMoved.ANY_COMMIT:
            kwargs['C'] = [True, True, True]

        bug_introduce_commits = set()
        mod_line_ranges = self._parse_line_ranges()
        print(mod_line_ranges)

        # sort entry by the datetime
        sorted_entry = [(entry, entry.commit.committed_datetime,)
                                for entry in self._repository.blame_incremental(
                                                **kwargs, rev=rev, L=mod_line_ranges, file=file_path)]
        sorted_entry = sorted(sorted_entry, key=lambda x: x[1], reverse=True)

        commit_map_dict = dict()
        entry_map_dict = dict()
        file_change_dict = dict()
        for entry_tuple in sorted_entry:
            print('---blame--\n', entry_tuple[0].commit)
            for i, lineno in enumerate(entry_tuple[0].linenos):
                if entry_tuple[0].commit not in entry_map_dict:
                    #new_lineno, old_lineno
                    entry_map_dict[entry_tuple[0].commit] = [((lineno, entry_tuple[0].orig_linenos[i]))]
                else:
                    entry_map_dict[entry_tuple[0].commit].append((lineno, entry_tuple[0].orig_linenos[i]))

            mapped_line_map, blame_file_path = \
                self.map_modified_line(rev, entry_tuple[0], file_path)
            if entry_tuple[0].commit.hexsha not in file_change_dict:
                file_change_dict[entry_tuple[0].commit.hexsha] = blame_file_path

            if mapped_line_map == -1: #new file
                self.introduce_commit.append(entry_tuple[0].commit)
                continue
            # mapped_line_map {‘after commit line’: 'previous commit same line'}

            # 合并同一个commit的mod结果
            if entry_tuple[0].commit not in commit_map_dict:
                commit_map_dict[entry_tuple[0].commit] = mapped_line_map
            else:
                commit_map_dict[entry_tuple[0].commit].update(mapped_line_map)

            '''
            for lineno in entry_tuple[0].orig_linenos:
                if len(mapped_line_map[lineno]) == 0:
                    print(f'[warning]{entry_tuple[0].commit} exists new line, stop traversal')
            '''

        delete_commit = list()
        for commit in commit_map_dict:
            score = self.calculate_diff_score(commit_map_dict, commit)
            if commit.hexsha not in self.score_map:
                self.score_map[commit.hexsha] = score
            else:
                self.score_map[commit.hexsha] += score
            print(commit, self.score_map[commit.hexsha], self.score_map[commit.hexsha]/self.overall_score)
            change_ratio = self.score_map[commit.hexsha]/self.overall_score
            if change_ratio > 0.4:
                print(f'[warning]{commit} exists new line, stop traversal')
                self.introduce_commit.append(commit)
                if commit not in self.introduce_commit:
                    delete_commit.append(commit)
            #elif change_ratio < 0.5 and change_ratio > 0:
                #delete_commit.append(commit)
        for c in delete_commit:
            del commit_map_dict[c]

        for commit in commit_map_dict:
            self.vul_lineno_list = list()
            for new_line in commit_map_dict[commit]:
                self.vul_lineno_list.extend(commit_map_dict[commit][new_line])
            self.vul_lineno_list = sorted(self.vul_lineno_list, reverse=False)
            if self.vul_lineno_list == []: continue

            #TODO: get the previous commit (git log)
            self.blame(rev='{commit_id}^'.format(commit_id=commit.hexsha), file_path=file_change_dict[commit.hexsha])



