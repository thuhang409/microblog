from openai import OpenAI
from app import app


def translate(text, source_language, dst_language):
    print(app.config['OPENAI_API_KEY'])
    if 'OPENAI_API_KEY' not in app.config or not app.config['OPENAI_API_KEY']:
        return 'Error: OPENAI_API_KEY is missing.'

    client = OpenAI(api_key=app.config['OPENAI_API_KEY'])
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