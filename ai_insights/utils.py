from groq import Groq
from django.conf import settings
import re

# Function to get insights from GroqCloud
def get_insights(ai_goal):
    try:
        print(f"Fetching insights for goal: {ai_goal}")
        # Initialize Groq client with API key
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Make the API call to Groq
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
           # messages=[
           #     {
            #        "role": "user",
            #        "content": f"my goal is {ai_goal}, how do I get there...break down this goal for me into actionable tasks with realistic timelines. Please provide the response in the exact format below, with no additional text outside the specified structure:\n\n
            # **Step 1: [Title] (X-X weeks)**\n1. **[Subtask Title]**: [Details about the subtask with timeline (X-X days/weeks/months)]\n\n**Step 2: [Title] (X-X weeks)**\n1. **[Subtask Title]**: [Details about the subtask with timeline (X-X days/weeks/months)]\n\nEnsure every step has a title, timeline, and clear subtasks with detailed timelines."
            #
            #               }
            #          ],

            messages=[
                {
                    "role": "user",
                    "content": f"My goal is {ai_goal}. First, classify this goal into one of the following categories:  'Weekly', 'Monthly', or 'Yearly'. Then, break it down into actionable tasks with realistic timelines. Ensure the response follows this exact format:\n\n"
                            "**Goal Category: [ Weekly / Monthly / Yearly]**\n\n"
                            "**Step 1: [Title] (X-X weeks/months/years)**\n"
                            "1. **[Subtask Title]**: [Details about the subtask with timeline (X-X days/weeks/months/years)]\n\n"
                            "**Step 2: [Title] (X-X weeks/months/years)**\n"
                            "1. **[Subtask Title]**: [Details about the subtask with timeline (X-X days/weeks/months/years)]\n\n"
                            "Ensure each goal has a category, and each step has a title, timeline, and clear subtasks with detailed timelines."
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

        print(f"Raw response: {response}")

        # Parse the response into a list of actionable steps
        steps = parse_insights(response)
        print(f"Parsed steps: {steps}")
        return steps

    except Exception as error:
        print(f"Error generating insights: {error}")
        raise ValueError("Failed to fetch insights from GroqCloud.")
    
def parse_insights(response):
    """
    Parses the AI response into a structured list of steps.
    """
    category_match = re.search(r'\*\*Goal Category:\s*(Weekly|Monthly|Yearly)\*\*', response)
    goal_category = category_match.group(1).lower()  if category_match else "Uncategorized"

    # Split the response into steps based on the format "**Step X: [Title] (X-X weeks)**"
    steps = re.split(r'\*\*Step \d+:\s*', response)
    parsed_steps = []

    for step in steps[1:]:  # Skip the first part as it will not be a valid step
        # Extract the step title and timeline using the specified format
        title_match = re.search(r'(.+?)\s*\((.+?)\)', step)
        if title_match:
            title = title_match.group(1).strip()
            task_timeline = title_match.group(2).strip()
        else:
            continue  # Skip if no title or timeline is found

        # Extract actionable steps using bullet points and subtasks format
        subtask_matches = re.findall(
            r'\d+\.\s\*\*(.+?)\*\*:\s*(.+?)(?=\n\d+\.\s\*\*|$)', 
            step, 
            re.DOTALL
        )

        ai_subtasks = []

        for match in subtask_matches:
            subtask_title = match[0].strip()
            details = match[1].strip()
            ai_subtasks.append({
                "subtask_title": subtask_title,
                "description": details,
            })

        # Append the parsed step into the list
        parsed_steps.append({
            "task_title": title,
            "task_timeline": task_timeline,
            "ai_subtasks": ai_subtasks,
        })

    return {
        "goal_category": goal_category,
        "tasks": parsed_steps
    }
