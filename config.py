# Page Configuration
PAGE_TITLE = "Learn Python from Scratch as a Beginner"
PAGE_LAYOUT = "wide"

# Learning Objectives
LEARNING_OBJECTIVES = [
    "Introduction to Python and its applications",
    "Write your first Python program",
    "Understand variables and data types",
    "Work with user input and type conversion",
    "Manipulate strings and use arithmetic operators",
    "Use comparison and logical operators",
    "Implement conditional statements (if-else)",
    "Create and use while loops",
    "Work with lists and their methods",
    "Utilize for loops and the range() function",
    "Understand and use tuples"
]

# Prompts
SYSTEM_MESSAGE_QUERY_GENERATION = "Given the following conversation and the user's final question, rephrase the final question to be a standalone question. Keep it short but capture everything that's relevant"

# Dynamic System Message for Tutor
def get_system_message_tutor(current_objective):
    objective_messages = {
        0: "Introduce Python and its various applications in different fields.",
        1: "Guide the student through writing their first Python program, explaining basic syntax and structure.",
        2: "Explain the concept of variables, their naming conventions, and different data types in Python.",
        3: "Teach how to receive user input and perform type conversion between different data types.",
        4: "Demonstrate string manipulation techniques and explain arithmetic operators and their precedence.",
        5: "Introduce comparison and logical operators, showing how they're used in Python.",
        6: "Explain conditional statements, focusing on if-else structures and their usage.",
        7: "Introduce while loops, explaining their syntax and when to use them.",
        8: "Teach about lists, their properties, and common methods used with lists.",
        9: "Explain for loops and how to use the range() function for iteration.",
        10: "Introduce tuples, their properties, and how they differ from lists."
    }
    
    base_message = """You are Mosh, an AI assistant created by the youtuber, Mosh teaching Python programming. Your sole focus at this moment is on getting the user through the following objective: "{objective}". If you believe the student has completed the current objective, add "OBJECTIVE_COMPLETED" at the end of your response.
    Make sure to keep the discussion focused on the current objective. Keep it light, playful, and engaging. You will be interacting with a complete beginner so you have to be methodical and prescriptive.

Your role is to:
1. Explain concepts clearly and simply.
2. Take things step by step. Don't overwhelm the user with a lot of information at once.
3. Provide code examples when appropriate.
4. Offer gentle corrections for misconceptions or errors.

You are currently playing out one objective of the course. The entire course contains the following objectives, JFYI:
    "Introduction to Python and its applications",
    "Write your first Python program",
    "Understand variables and data types",
    "Work with user input and type conversion",
    "Manipulate strings and use arithmetic operators",
    "Use comparison and logical operators",
    "Implement conditional statements (if-else)",
    "Create and use while loops",
    "Work with lists and their methods",
    "Utilize for loops and the range() function",
    "Understand and use tuples"

Here are some references from the videos you have on this topic:\n\n{context}"""

    return base_message.format(objective=objective_messages.get(current_objective, "Python programming"), context="{context}")

# Replace the static SYSTEM_MESSAGE_TUTOR with this function
# SYSTEM_MESSAGE_TUTOR = get_system_message_tutor(current_objective)

# S3 Configuration
S3_BUCKET = "zoe-images"

# Pinecone Configuration
PINECONE_INDEX_NAME = "project-management"
PINECONE_NAMESPACE = "programming_with_mosh_python_for_beginners"

# OpenAI Models
MODEL_QUERY_GENERATION = "gpt-4o"
MODEL_CHAT = "gpt-4o"

# Custom CSS
CUSTOM_CSS = """
<style>
.sidebar .element-container {
    margin-bottom: 10px;
}
.steps-container h3 {
    display: flex;
    align-items: center;
    font-size: 18px;
    margin-bottom: 10px;
}
.target-emoji {
    font-size: 18px;
    margin-right: 10px;
}
.steps {
    position: relative;
}
.step {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    position: relative;
    z-index: 1;
}
.circle {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    margin-right: 10px;
    border: 2px solid #4285f4;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: white;
    font-size: 12px;
    color: #4285f4;
}
.active .circle::after {
    content: '';
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: #4285f4;
}
.completed .circle::after {
    content: '✓';
    font-weight: bold;
}
.step-text {
    font-size: 14px;
}
.active-text {
    font-weight: bold;
}
.inactive-text {
    color: #5f6368;
}
.completed-text {
    color: #9aa0a6;
}
.progress-line {
    position: absolute;
    left: 11px;
    top: 20px;
    bottom: 20px;
    width: 2px;
    background-image: linear-gradient(to bottom, #4285f4 50%, transparent 50%);
    background-size: 2px 8px;
    background-repeat: repeat-y;
}
</style>
"""
