import Levenshtein
import re, sys

vul_method_keyword = ['read', 'write', 'memset', 'malloc', 'Malloc', 'zalloc', 'memcpy', 'free', 'strcmp', 'strcpy', 'strdup',
                      'sprintf', 'printf', 'strcat', 'get_line_size']
MAXSIZE = sys.maxsize

def remove_whitespace(line_str):
    return ''.join(line_str.strip().split())

def compute_line_ratio(line_str1, line_str2):
    l1 = remove_whitespace(line_str1)
    l2 = remove_whitespace(line_str2)
    return Levenshtein.ratio(l1, l2)

class Node:
    def __init__(self):
        self.kind = None
        self.content = None
        self.children = list()

    def __str__(self):
        if self.kind and self.content:
            return "".join(["kind:", self.kind, "\tcontent:", self.content])
        else:
            return "".join(["kind:", self.kind])

def rm_comments(code_text):
    # remove the comments such as: //xxxx\n; /* xxx\nxxxx */
    comment_pattern1 = '\/\/[^\n]+\n'
    comment_pattern2 = '\/\*[\s\S]*?\*\/'
    spans = []
    for res in re.finditer(comment_pattern2, code_text):
        spans.append(res.span())
    for res in re.finditer(comment_pattern1, code_text):
        a, b, = res.span()
        spans.append((a, b - 1))  # do not remove the "\n"! e.g. +b=1\\com\n+ if(a) b=a;
    spans.sort()
    spans.append((len(code_text), len(code_text)))
    start = 0
    pure_code = ""
    for spani, spanj in spans:
        pure_code += code_text[start:spani]
        start = spanj
    return pure_code

def longest_common_substring(str1, str2):
    m = len(str1)
    n = len(str2)

    # 创建二维动态规划表格
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 记录最长公共子字符串的长度和结束位置
    max_length = 0
    end_pos = 0

    # 填充动态规划表格
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                if dp[i][j] > max_length:
                    max_length = dp[i][j]
                    end_pos = i

    # 获取最长相同子字符串
    longest_substring = str1[end_pos - max_length: end_pos]

    return longest_substring

def compare_file_sim(file1, file2):
    with open(file1, 'r') as file1:
        lines1 = set(file1.readlines())
    with open(file2, 'r') as file2:
        lines2 = set(file2.readlines())

    # 计算并集和交集
    union = lines1.union(lines2)
    intersection = lines1.intersection(lines2)

    # 计算 Jaccard 系数
    jaccard_similarity = len(intersection) / len(union)

    return jaccard_similarity

