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
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"My goal description is {ai_goal}. "
                        "First, give this goal description a suitable title and tag then classify this goal into one of the following categories: 'Weekly', 'Monthly', or 'Yearly'. "
                        "Then, break it down into actionable tasks with realistic timelines. "
                        "Ensure the response follows this exact format and *contains ONLY this format, with no additional introductory or concluding remarks*:\n\n"
                        "**Goal Title: [Title]**\n\n"
                        "**Goal Tag: [Tag]**\n\n"
                        "**Goal Category: [ Weekly / Monthly / Yearly]**\n\n"
                        "**Step 1: [Title] (X-X weeks/months/years) **\n"
                        "1. **[Subtask Title]**: [A clear, concise description of the subtask.] **Timeline:** [e.g., '2–4 days', '1–2 weeks']"
                        "\n\n" 
                        "**Step 2: [Title] (X-X weeks/months/years)**\n"
                        "1. **[Subtask Title]**: [A clear, concise description of the subtask.] **Timeline:** [e.g., '2–4 days', '1–2 weeks']"
                        "Ensure each goal has a category, and each step has a title, timeline, and clear subtasks with detailed descriptions and timelines."
                        )
                }
            ],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False, # Changed to False for simplicity in this example
            stop=None
        )

        # Extract the message content from the response
        response = completion.choices[0].message.content
        print(f"Raw response: {response}")

        # Parse the response into a list of actionable steps
        steps = parse_insights(response)
        print(f"Parsed steps: {steps}")
        return steps

    except Exception as error:
        print(f"Error generating insights: {error}")
        raise ValueError("Failed to fetch insights from GroqCloud.")
EMOJI_MAP = {
    # General Work & Development
    "research": "🔍",
    "plan": "📝",
    "design": "🎨",
    "develop": "💻",
    "code": "💻",
    "build": "🏗️",
    "test": "🧪",
    "debug": "🪲",
    "deploy": "🚀",
    "launch": "🚀",
    "feedback": "📊",
    "analyze": "📊",
    "review": "🔎",
    "setup": "⚙️",
    "integrate": "🔗",
    "configure": "⚙️",
    "marketing": "📣",
    "create": "✨",
    "write": "✍️",
    "learn": "📚",
    "prototype": "📐",
    "persona": "🧑‍🎨",
    "cloud": "☁️",
    "performance": "📈",

    # Health & Nutrition Specific
    "track": "📖",
    "eat": "🍽️",
    "meal": "🍱",
    "food": "🥗",
    "snack": "🍌",
    "calorie": "🔥",
    "weight": "⚖️",
    "hydrate": "💧",
    "drink": "🥤",
    "water": "🚰",
    "sleep": "🛌",
    "rest": "🛏️",
    "exercise": "🏋️",
    "nutrition": "🥑",
    "groceries": "🛒",
    "cook": "👨‍🍳",
    "prepare": "🍳",
    "doctor": "👨‍⚕️",
    "dietitian": "👩‍⚕️",
    "health": "🩺",
    "motivate": "🎯",
    "motivation": "🎯",
    "goal": "🏁",
    "default": "✅"
}

def parse_insights(response):
    """
    Parses the AI response into a structured list of steps.
    """
    goal_title_match = re.search(r'\*\*Goal Title:\s*(.+?)\*\*', response)
    goal_title = goal_title_match.group(1).strip() if goal_title_match else "Untitled Goal"
    goal_tag_match = re.search(r'\*\*Goal Tag:\s*(.+?)\*\*', response)
    goal_tag = goal_tag_match.group(1).strip() if goal_tag_match else "No Tag"
    category_match = re.search(r'\*\*Goal Category:\s*(Weekly|Monthly|Yearly)\*\*', response)
    goal_category = category_match.group(1).lower()  if category_match else "Uncategorized"

    # Truncate the response after the last valid subtask pattern
    subtask_pattern = r'\d+\.\s\*\*.+?\*\*:\s*.+?(?=\n\d+\.\s\*\*|$)'
    all_subtasks = list(re.finditer(subtask_pattern, response, re.DOTALL))
    if all_subtasks:
        last_subtask = all_subtasks[-1]
        response = response[:last_subtask.end()]


    # Split the response into steps based on the format "**Step X: [Title] (X-X weeks)**"
    steps = re.split(r'\*\*Step \d+:\s*', response)
    parsed_steps = []

    for step in steps[1:]:  # Skip the first part as it will not be a valid step
        # Extract the step title and timeline using the specified format
        title_match = re.search(r'(.+?)\s*\((.+?)\)', step)
        if title_match:
            title = title_match.group(1).strip()
            # Attach emoji to task title
            lower_title = title.lower()
            for key, emoji in EMOJI_MAP.items():
                if key in lower_title:
                    title = f"{emoji} {title}"
                    break
            else:
                title = f"{EMOJI_MAP['default']} {title}"

            task_timeline = title_match.group(2).strip()

           
        else:
            continue  # Skip if no title or timeline is found

        # Extract actionable steps using bullet points and subtasks format
        subtask_matches = re.findall(
            r'\d+\.\s\*\*(.+?)\*\*:\s*(.+?)(?=\n\d+\.\s\*\*|$)', 
            step, 
            re.DOTALL
        )

        # If there are matches, slice the step up to the end of the last match to remove anything after
       
        ai_subtasks = []

        for match in subtask_matches:
            subtask_title = match[0].strip()
            details = match[1].strip()
            # Add emoji to subtask title
            lower_subtask = subtask_title.lower()
            for key, emoji in EMOJI_MAP.items():
                if key in lower_subtask:
                    subtask_title = f"{emoji} {subtask_title}"
                    break
            else:
                subtask_title = f"{EMOJI_MAP['default']} {subtask_title}"



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
        "goal_title": goal_title,
        "goal_category": goal_category,
        "goal_tag": goal_tag,
        "tasks": parsed_steps
    }



def answer_subtask_question(title, description):
    try:
        print(f"Answering subtask: {title}")
        client = Groq(api_key=settings.GROQ_API_KEY)

           # Add emoji to title
        lower_title = f"{title} {description}".lower()
        for key, emoji in EMOJI_MAP.items():
            if key in lower_title:
                title = f"{emoji} {title}"
                break
        else:
            title = f"{EMOJI_MAP['default']} {title}"

        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "user",
                    "content": f"Help me tackle this task:\n\n"
                            f"**Task Title:** {title}\n\n"
                            f"**Description:** {description}\n\n"
                        "Give me a clear and complete explanation. Assume I know nothing. Avoid asking me to search or read external resources. Just explain everything I need to know in your own words."

                }
            ],
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=False,
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error answering subtask: {e}")
        return "No answer available."
