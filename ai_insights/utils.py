from django.utils import timezone
from datetime import timedelta
from groq import Groq
from django.conf import settings
import re
from goals.models import AiSubTask, AiTask, AiGoal, Task
from .models import AIInsight
from users.models import User, UserActivity
import pytz


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




def answer_subtask_question(subtask: AiSubTask):
    try:
        print(f"Answering ai subtask")
        client = Groq(api_key=settings.GROQ_API_KEY)

        ai_task = subtask.ai_task
        ai_goal = ai_task.ai_goal if ai_task else None

        # 🧠 Build contextual message for LLM
        context_parts = []
        if ai_goal:
            context_parts.append(f"Goal: {ai_goal.title}")
        if ai_task:
            context_parts.append(f"Task: {ai_task.title}\nDescription: {ai_task.description or 'No description'}")

        context_parts.append(f"Subtask: {subtask.title}\nDescription: {subtask.description or 'No description'}")
        context = "\n\n".join(context_parts)

      

        # 🧩 Build message
        messages = [
            {
                "role": "user",
                "content": (
                    f"You are an AI assistant helping me complete my goals.\n\n"
                    f"Here is the full context:\n{context}\n\n"
                    f"Now, please help me understand and tackle the **subtask**:\n\n"
                    f"**Subtask Title:** {subtask.title}\n"
                    f"Explain clearly what to do, step-by-step. "
                    f"Assume I have no prior knowledge. Do not tell me to look up things online — explain everything in your own words."
                )
            }
        ]

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=False,
        )

        answer = completion.choices[0].message.content.strip()

        # 💾 Save to insights for history/reference
        AIInsight.objects.create(
            ai_goal=ai_goal,
            ai_task=ai_task,
            ai_subtask=subtask,
            insight_text=answer
        )

        return answer

    except Exception as e:
        print(f"Error answering subtask: {e}")
        return "No answer available."





def answer_task_question(task: Task):
    try:
        print(f"Answering task: {task.title}")
        client = Groq(api_key=settings.GROQ_API_KEY)

        goal = task.goal
        context_parts = []

        # 🧠 Include goal context if available
        if goal:
            context_parts.append(
                f"Goal: {goal.title}\nDescription: {goal.description or 'No description provided.'}"
            )

        # 🧩 Include task context
        context_parts.append(
            f"Task: {task.title}\nDescription: {task.description or 'No description provided.'}"
        )

        context = "\n\n".join(context_parts)

      

        # 🧩 Build message
        messages = [
            {
                "role": "user",
                "content": (
                    f"You are an AI assistant helping me complete my goals.\n\n"
                    f"Here is the full context:\n{context}\n\n"
                    f"Now, please help me understand and tackle the **task**:\n\n"
                    f"**Task Title:** {task.title}\n"
                    f"Explain clearly what to do, step-by-step. "
                    f"Assume I have no prior knowledge. Do not tell me to look up things online — explain everything in your own words."
                )
            }
        ]

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=False,
        )

        answer = completion.choices[0].message.content.strip()

        # 💾 Save to insights for history/reference
        if getattr(task, "goal", None):  # only if your Task model has a goal field
            AIInsight.objects.create(
                ai_goal=task.goal,
                task=task,
                insight_text=answer
            )
        else:
            AIInsight.objects.create(
                task=task,
                insight_text=answer
            )


        return answer

    except Exception as e:
        print(f"Error answering task: {e}")
        return "No answer available."




def generate_weekly_activity_feedback(user):
    now = timezone.now()
    week_start = now - timedelta(days=7)

    # Get all activity logs for the user in the last week
    activities = UserActivity.objects.filter(user=user, timestamp__gte=week_start)
    if not activities.exists():
        return None

    # Extract patterns
    active_days = activities.datetimes("timestamp", "day")
    inactive_days = [day.strftime("%A") for day in (week_start + timedelta(days=i) for i in range(7))
                     if day.date() not in [a.date() for a in active_days]]
    
    # Determine most active time (hour range)
    hours = [a.timestamp.astimezone(pytz.timezone(user.timezone)).hour for a in activities]
    most_active_hour = max(set(hours), key=hours.count)
    if 5 <= most_active_hour < 12:
        productive_time = "morning 🌅"
    elif 12 <= most_active_hour < 17:
        productive_time = "afternoon ☀️"
    else:
        productive_time = "evening 🌙"

    # Compare consistency with last week
    last_week_start = week_start - timedelta(days=7)
    last_week_activities = UserActivity.objects.filter(user=user, timestamp__range=(last_week_start, week_start))
    consistency_change = len(activities) - len(last_week_activities)
    trend = "increased" if consistency_change > 0 else "dropped"

    # --- AI summary ---
    client = Groq(api_key=settings.GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Generate a short motivational weekly activity summary for {user.first_name}. "
                    f"They were active on {len(active_days)} days this week, mostly in the {productive_time}. "
                    f"Inactive days: {', '.join(inactive_days) or 'none 🎉'}. "
                    f"Their consistency {trend} compared to last week. "
                    f"Keep the tone friendly, motivational, and concise (3-5 sentences max)."
                )
            }
        ],
    )
    insight_text = completion.choices[0].message.content.strip()

    AIInsight.objects.create(user=user, insight_text=insight_text)
    return insight_text