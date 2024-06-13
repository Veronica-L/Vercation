import openai

openai.api_key = "xxxxxx"

def generate_prompt_and_completion(cve_data, prompt_end = "\n####\n", completion_end = "\n<|endoftext|>"):
    ret_dict = {}
    ret_dict['prompt'] = cve_data['text'] + prompt_end ##

    if cve_data['in_training']:
        ret_dict['logic'] = cve_data["logic"]
        ret_dict['lines'] = cve_data["lines"]
        ret_dict['completion'] = '\n' + ret_dict['logic'] + '\n' + ret_dict['lines'] + completion_end

    return ret_dict
def chat_with_gpt(few_shot_prompt):
    client = openai.OpenAI(
        api_key=openai.api_key,
    )

    completion = client.chat.completions.create(  # Change the method
        model="gpt-4-0613",
        # model = "gpt-3.5-turbo",
        messages=[  # Change the prompt parameter to messages parameter
            {"role": "system",
             "content": "You are a security researcher, expert in detecting security vulnerabilities."},
            {"role": "user", "content": few_shot_prompt},
        ],
        temperature=0
    )
    response_content = completion.choices[0].message.content.strip()
    return response_content

