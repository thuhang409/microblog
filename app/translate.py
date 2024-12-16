from openai import OpenAI
from flask import current_app


def translate(text, source_language, dst_language):
    print(current_app.config['OPENAI_API_KEY'])
    if 'OPENAI_API_KEY' not in current_app.config or not current_app.config['OPENAI_API_KEY']:
        return 'Error: OPENAI_API_KEY is missing.'

    client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant who translates text."},
            {
                "role": "user",
                "content": f"Translate the following text into {dst_language} accurately without redundancy, no explain:\n{text}"
            }],
            temperature=0.5,
            top_p=1.0

    )
        
    return completion.choices[0].message.content.strip()