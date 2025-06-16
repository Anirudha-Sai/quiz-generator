import streamlit as st
from groq import Groq
import json
import random
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Quiz Generator (via )",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- App Title and Description ---
st.title("⚡ AI Quiz Generator")
st.write("Paste your notes, and this app will generate a quiz for you using free, high-speed AI models from Groq. Perfect for students and learners!")

# --- List of Free Models Available on Groq ---
GROQ_MODELS = [
    "llama3-8b-8192",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
]

# --- API Key Handling ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
except KeyError:
    st.error("Groq API Key not found. Please add your key to Streamlit secrets.", icon="🚨")
    st.info("Create a `.streamlit/secrets.toml` file with: `GROQ_API_KEY = 'your_key_here'`")
    st.stop()

# --- Helper function for validation ---
def validate_quiz_data(quiz_data):
    """Checks if the quiz data from the AI is in the correct format."""
    if not isinstance(quiz_data, list):
        st.error("AI did not return a list of questions. Please try again.")
        return None

    validated_questions = []
    for q in quiz_data:
        if not isinstance(q, dict):
            continue # Skip items that are not dictionaries
        if "question" in q and "options" in q and "answer" in q:
            if isinstance(q["options"], list) and len(q["options"]) == 4:
                if q["answer"] in q["options"]:
                    validated_questions.append(q)
    
    if not validated_questions or len(validated_questions) < len(quiz_data):
        st.warning("Some questions were malformed by the AI and have been excluded.")

    return validated_questions if validated_questions else None

# --- Core Function to Generate Quiz ---
def generate_quiz_from_notes(notes_text, num_questions, difficulty, model):
    """Calls the Groq API to generate a quiz and validates the response."""
    client = Groq(api_key=api_key)
    prompt = f"""
    You are an expert quiz designer. Your task is to create a multiple-choice quiz from the provided text.

    **Instructions:**
    1. Generate exactly {num_questions} questions of '{difficulty}' difficulty.
    2. Each question must have exactly 4 options. One option must be the correct answer.
    3. Ensure the options are relevant and plausible to make the quiz challenging.
    4. Your response **MUST** be a valid JSON array of objects. Do not include any text, explanations, or markdown before or after the JSON array.
    5. Each JSON object must have three keys: "question", "options" (a list of 4 strings), and "answer" (the string of the correct option).

    **Text to use for the quiz:**
    ---
    {notes_text}
    ---
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates quizzes in a structured JSON format."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        quiz_json_string = response.choices[0].message.content
        quiz_data = json.loads(quiz_json_string)
        
        # Models sometimes wrap the list in a dictionary. This finds the list.
        if isinstance(quiz_data, dict):
            for key, value in quiz_data.items():
                if isinstance(value, list):
                    return validate_quiz_data(value)
        elif isinstance(quiz_data, list):
            return validate_quiz_data(quiz_data)
            
        st.error("The AI returned an unexpected JSON structure. Please try again.")
        return None
        
    except Exception as e:
        st.error(f"An API error occurred: {e}")
        return None

# --- Streamlit Sidebar for User Input ---
with st.sidebar:
    st.header("⚙️ Quiz Settings")
    notes_input = st.text_area("Paste your notes or text here", height=250, key="notes_input")
    num_questions = st.slider("Number of Questions", min_value=1, max_value=10, value=5)
    difficulty = st.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
    selected_model = st.selectbox("Select AI Model", GROQ_MODELS)
    generate_button = st.button("Generate Quiz", use_container_width=True, type="primary")

# --- Session State Initialization ---
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = []

# --- Main App Logic ---
if generate_button:
    if not st.session_state.notes_input.strip():
        st.warning("Please paste some notes before generating the quiz.")
    else:
        with st.spinner("Generating your quiz with Groq... This should be fast! ⚡"):
            quiz_data = generate_quiz_from_notes(st.session_state.notes_input, num_questions, difficulty, selected_model)
            if quiz_data:
                st.session_state.quiz_data = quiz_data
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.session_state.user_answers = [None] * len(quiz_data)
                st.success(f"Quiz generated with {len(quiz_data)} questions!")
                st.rerun()
            else:
                st.error("Could not generate a valid quiz. Please adjust your notes or model and try again.")
                st.session_state.quiz_data = None # Ensure old quiz is cleared

# --- Quiz Display and Interaction ---
if st.session_state.quiz_data:
    q_index = st.session_state.current_question
    total_questions = len(st.session_state.quiz_data)

    if q_index < total_questions:
        question_data = st.session_state.quiz_data[q_index]
        
        st.progress((q_index) / total_questions, text=f"Question {q_index + 1} of {total_questions}")
        st.subheader(question_data.get("question", "No question text found."))
        
        with st.form(key=f"question_form_{q_index}"):
            options = question_data.get("options", [])
            
            # THE FIX: Assign a unique key to the radio button
            user_choice = st.radio(
                "Choose your answer:", 
                options, 
                index=None, 
                key=f"radio_{q_index}"
            )
            
            submit_button = st.form_submit_button("Submit Answer")

            if submit_button:
                if user_choice is not None:
                    st.session_state.user_answers[q_index] = user_choice
                    correct_answer = question_data.get("answer")
                    if user_choice == correct_answer:
                        st.session_state.score += 1
                        st.success("Correct! 🎉")
                    else:
                        st.error(f"Incorrect. The correct answer was: **{correct_answer}**")
                    
                    time.sleep(1.5)
                    st.session_state.current_question += 1
                    st.rerun()
                else:
                    st.warning("Please select an answer before submitting.")
    else:
        st.header("🎉 Quiz Finished! 🎉")
        st.subheader(f"Your Final Score: {st.session_state.score} / {total_questions}")

        with st.expander("📝 Review Your Answers"):
            for i, q in enumerate(st.session_state.quiz_data):
                st.markdown(f"**Question {i+1}:** {q['question']}")
                user_ans = st.session_state.user_answers[i]
                correct_ans = q['answer']
                if user_ans == correct_ans:
                    st.markdown(f"✅ Your Answer: `{user_ans}` (Correct)")
                else:
                    st.markdown(f"❌ Your Answer: `{user_ans}`")
                    st.markdown(f"**Correct Answer:** `{correct_ans}`")
                st.divider()

        if st.button("Take a New Quiz", use_container_width=True):
            st.session_state.clear()
            st.rerun()
