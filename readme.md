## Introduction
This is the source code package for paper "Vercation: Precise Vulnerable Open-source Software Versions Identification based on Static Analysis and LLM"

> A tool for identifying vulnerable versions of OSS project writen by C/C++

## Prerequisites

- Python environment: Python 3.8
- Requirements: `pip install -r requirements.txt`

## Running
We provide test vulnerability data in `data/patch.txt`
Run `run.py` to get the vulnerability-introducing commit (vic)
```bash
python3 run.py {oss_name}
```
It will output the vic info into `data/result.txt`

Run `extract_tag.py` to get the vulnerable version tags

```bash
python3 extact_tag.py {vulnerability-introducing commit} {patch commit}
```

## Test
If you want to test in your own vulnerability data
- Install Joern Parser (refer to https://github.com/joernio/joern)
- In the Joern workspace, use `cpg.method($name).dotDdg.l > ddg.json` to generate DDG, CFG and AST as the same, then put the result into `json` folder
- Provide the patch information of vulnerability like `data/patch.txt` folder
- Provide your own opensi key in `LLM/gpt_use.py`