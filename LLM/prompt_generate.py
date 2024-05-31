from LLM.few_shot import get_few_shot

def gen_df_str(df):
    sorted_values = sorted(df.keys())
    df_str = ''

    for i in sorted_values:
        df_str += f'{i}  {df[i]}\n'
    return df_str

def generate_prompt_and_completion(cve_data, prompt_end = "\n####\n", completion_end = "\n<|endoftext|>"):
    ret_dict = {}
    ret_dict['prompt'] = cve_data['text'] + prompt_end ##

    if cve_data['in_training']:
        ret_dict['logic'] = cve_data["logic"]
        ret_dict['lines'] = cve_data["lines"]
        ret_dict['completion'] = '\n' + ret_dict['logic'] + '\n' + ret_dict['lines'] + completion_end

    return ret_dict

def gen_prompt(df, cve_info):
    df_str = gen_df_str(df)
    cve_list = get_few_shot(df_str, cve_info)
    training_list = []
    to_predict_list = []
    for review in cve_list:
        if review['in_training']:
            training_list.append(generate_prompt_and_completion(review))
        else:
            to_predict_list.append(generate_prompt_and_completion(review))

    few_shot_examples = ''
    for training_item in training_list[:2]:
        few_shot_examples += training_item['prompt']
        few_shot_examples += training_item['completion'] + '\n'

    few_shot_prompt = few_shot_examples + to_predict_list[0]['prompt']
    return few_shot_prompt

