import subprocess
import os
from git_analysis.analyze_git_logs import retrieve_git_logs, retrieve_git_logs_dict

class GitLog:
    commands = {
        'meta': 'meta_cmd',
        'numstat': 'numstat_cmd',
        'namestat': 'namestat_cmd',
        'merge_numstat': 'merge_numstat_cmd',
        'merge_namestat': 'merge_namestat_cmd'
    }

    def __init__(self):
        self.meta_cmd = 'git log --reverse --all --pretty=format:\"commit: %H%n' \
                        'parent: %P%n' \
                        'author: %an%n' \
                        'author email: %ae%n' \
                        'time stamp: %at%n' \
                        'committer: %cn%n' \
                        'committer email: %ce%n' \
                        '%B%n\"  '
        self.numstat_cmd = 'git log --pretty=format:\"commit: %H\" --numstat -M --all --reverse '
        self.namestat_cmd = 'git log  --pretty=format:\"commit: %H\" --name-status -M --all --reverse '
        self.merge_numstat_cmd = 'git log --pretty=oneline --numstat -m --merges -M --all --reverse '
        self.merge_namestat_cmd = 'git log --pretty=oneline  --name-status -m --merges -M  --all --reverse '

    def git_log(self, project_path):
        os.chdir(project_path)

        cmd = getattr(self, GitLog.commands.get('meta'))
        out = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        return out

    def git_tag(self, project_path):
        os.chdir(project_path)

        cmd = 'git tag'
        out = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        return out

    def git_show(self, project_path, tag):
        os.chdir(project_path)

        cmd = 'git show {tag} --pretty=format:"commit: %H%ntimestamp: %ct%n"'.format(tag=tag)
        out = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        return out

def generate_logs(repo_dir, output):
    log_str = GitLog().git_log(repo_dir)
    print(os.getcwd())
    with open(output, 'w') as fout:
        fout.write(log_str)


def get_tags(repo_dir):
    output = GitLog().git_tag(repo_dir)
    tags = output.split('\n')

    commit_tag_map = {}
    for tag in tags:
        if tag.strip() == "":
            continue

        try:
            output = GitLog().git_show(repo_dir, tag)
        except Exception as e:
            print(tag, e)
            continue

        commit = None
        timestamp = None
        for line in output.split('\n'):
            if line.startswith('commit:'):
                commit = line[8:].strip()

            if line.startswith('timestamp:'):
                timestamp = line[11:].strip()
                break

        if commit is not None:
            commit_tag_map[commit] = tag

    return commit_tag_map

log_dir = 'meta'
repos_dir = '/home/cyr/mywork/VulLocate/source'
def generate_vulnerable_versions(project, fixing_commit, inducing_commit):
    git_logs = retrieve_git_logs(os.path.join(log_dir, project + "-meta.log"), project)
    git_log_dict = retrieve_git_logs_dict(git_logs, project)
    commit_tag_map = get_tags(os.path.join(repos_dir, project))
    for commit_id in git_log_dict:
        if commit_id in commit_tag_map:
            git_log_dict[commit_id].set_tag(commit_tag_map[commit_id])

        if len(git_log_dict[commit_id].parent) == 0:
            git_log_dict[commit_id].set_tag("Initial Commit")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('oss_name')
    parser.add_argument('patch_commit')
    parser.add_argument('introducing_commit')
    args = parser.parse_args()
    oss_name, patch_commit,introducing_commit = args.oss_name, args.patch_commit, args.introducing_commit
    #generate_logs('source/FFmpeg', '/home/cyr/mywork/VulLocate/meta/ffmpeg-meta.log')
    generate_vulnerable_versions(oss_name, patch_commit, introducing_commit)