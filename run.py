import json, argparse
from _core.get_patch_class import patchCommit, diff_prune
from _core.dependent_analysis import Dep
from _core.commit_lookback import myCommit
from _core.utils import vul_method_keyword
from LLM.prompt_generate import gen_prompt
from LLM.gpt_use import chat_with_gpt
import re

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('oss_name')
    args = parser.parse_args()
    oss_name = args.oss_name

    test_patch_file = open('data/patch.txt', 'r')
    wf = open('data/result.txt', 'a')
    for json_line in test_patch_file.readlines():
        patch_dict = json.loads(json_line)

        oss_name, patch_commit = patch_dict["oss_name"], patch_dict["commit"]
        p = patchCommit(repository_path=f'source/{oss_name}/{oss_name}', oss_name=oss_name, patch_commit=patch_commit, file=patch_dict["file"], patch_index=patch_dict["patch_index"])
        print(f'---{patch_dict["cve_number"]}---')
        print(f"oss name: {oss_name}, commit: {patch_commit}, file: {patch_dict['file']}")
        return_res, code_line_map_unpatch = p.retrieve_commit_content()
        taint_dict = diff_prune(return_res)
        print(taint_dict)


        for patch_file in return_res:
            for res in return_res[patch_file]:
                if "func_name" in patch_dict:
                    res._func_name = patch_dict["func_name"]
                else:
                    dep = Dep(oss_name=oss_name, commit=patch_commit, patch_info=res, taint_dict=taint_dict)
                    vul_lineno_list = dep.vul_lineno_list

                # TODO:get the code-line map of vul_lineno_list
                dangerous_flow_dict = {}
                for lineno in vul_lineno_list:
                    lineno_str = code_line_map_unpatch[lineno]
                    dangerous_flow_dict[str(lineno)] = lineno_str
                for i in res._add_lines:
                    dangerous_flow_dict[f"{i}+"] = res._add_lines[i]
                for j in res._delete_lines:
                    dangerous_flow_dict[f"{j}-"] = res._delete_lines[j]

                few_shot_prompt = gen_prompt(dangerous_flow_dict, patch_dict)
                #response_content = chat_with_gpt(few_shot_prompt)
                response_content = "vulnerable lines: [12096, 12099, 12101]"
                pattern = r"vulnerable lines: \[([^\]]+)\]"
                match = re.search(pattern, response_content)
                if match:
                    # Extracting the matched group which are the contents within the brackets
                    extracted_content = match.group(1)
                    # Splitting the contents by comma to get individual items as list
                    vulnerable_lines = [int(item.strip()) for item in extracted_content.split(',')]
                    print("Extracted vulnerable lines:", vulnerable_lines)
                else:
                    print("No vulnerable lines found.")

                '''
                vul_lineno_list_delete = list()
                for line in res._delete_lines:
                    code = res._delete_lines[line]
                    if code.strip().startswith('/*'):
                        continue
                    for k in vul_method_keyword:
                        if k in code:
                            vul_lineno_list_delete.append(line)
                            break
                if len(vul_lineno_list_delete) > 0:
                    vul_lineno_list = vul_lineno_list_delete
                    commit = myCommit(repository_path=f'source/{oss_name}/{oss_name}', oss_name=oss_name,
                                      patch_info=res, vul_lineno_list=vul_lineno_list, prompt='up')
                    commit.blame(rev='{commit_id}^'.format(commit_id=patch_commit), file_path=res._file_name)
                '''
                if len(vulnerable_lines) == 0:
                    vul_lineno_list = [int(lineno) for lineno in res._delete_lines]
                    commit = myCommit(repository_path=f'source/{oss_name}/{oss_name}', oss_name=oss_name,
                                      patch_info=res, vul_lineno_list=vul_lineno_list, prompt='up')
                    commit.blame(rev='{commit_id}^'.format(commit_id=patch_commit), file_path=res._file_name)
                else:
                    commit = myCommit(repository_path=f'source/{oss_name}/{oss_name}', oss_name=oss_name,
                                      patch_info=res, vul_lineno_list=vulnerable_lines, prompt='p')
                    commit.blame(rev='{commit_id}'.format(commit_id=patch_commit), file_path=res._file_name)

                print("---introduce commit---")
                wf.write(f'---{patch_dict["cve_number"]}---\n')
                for c in commit.introduce_commit:
                    print(c.hexsha, c.committed_datetime)
                    wf.write(f"{c.hexsha}, {c.committed_datetime}\n")



        