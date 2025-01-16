from groq import Groq
from django.conf import settings
import re

# Function to get insights from GroqCloud
def get_insights(goal):
    try:
        # Initialize Groq client with API key
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Make the API call to Groq
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "user",
                    "content": f"my goal is {goal}, how do I get there...break down this goal for me into actionable steps with realistic timelines"
                }
            ],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True,  # Change this to False if you don't want streaming
            stop=None
        )

        # Extract the message content from the response
        response = ""
        for chunk in completion:
            response += chunk.choices[0].delta.content or ""

        # Parse the response into a list of actionable steps
        steps = parse_insights(response)
        return steps

    except Exception as error:
        print(f"Error generating insights: {error}")
        raise ValueError("Failed to fetch insights from GroqCloud.")

def parse_insights(response):
    # Split the response into steps
    steps = re.split(r'\*\*Step \d+:', response)
    parsed_steps = []

    for step in steps[1:]:  # Skip the first split part as it will be empty
        # Extract the step title and actionable steps
        title_match = re.search(r'(.+?)\*\*', step)
        if title_match:
            title = title_match.group(1).strip()
            actionable_steps = re.findall(r'\d+\.\s(.+)', step)
            parsed_steps.append({
                "task_title": title,
                "actionable_steps": actionable_steps
            })

    return parsed_steps