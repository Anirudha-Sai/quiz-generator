import streamlit as st
import openai
import json

st.set_page_config(
    page_title="AI Notes-to-Quiz Generator",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 AI Notes-to-Quiz Generator")
st.write("Paste your notes, and this app will generate a quiz for you using AI. Perfect for students and learners!")

FREE_MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3-8b-instruct:free",
    "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
    "google/gemma-7b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
]
try:
    api_key = st.secrets["api"]["openrouter_api_key"]
except KeyError:
    st.error("API Key not found. Please add your OpenRouter API key to your Streamlit secrets.", icon="🚨")
    st.stop() 
def generate_quiz_from_notes(notes_text, num_questions, difficulty, model):
    client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    prompt = f"""
    You are an expert quiz designer. Your task is to create a multiple-choice quiz based on the provided text.
    Instructions:
    1.  Generate exactly {num_questions} questions of '{difficulty}' difficulty.
    2.  Each question must have exactly 4 options, with one being the correct answer.
    3.  Your response MUST be a valid JSON array of objects. Do not include any text outside the JSON array.
    4.  Each JSON object must have three keys: "question", "options" (a list of 4 strings), and "answer" (the correct option string).
    Text to use:
    ---
    {notes_text}
    ---
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to create quizzes in a structured JSON format."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        quiz_json_string = response.choices[0].message.content
        quiz_data = json.loads(quiz_json_string)
        if isinstance(quiz_data, dict):
            for key, value in quiz_data.items():
                if isinstance(value, list): return value
        elif isinstance(quiz_data, list):
            return quiz_data
        st.error("The AI returned an unexpected JSON structure. Please try again.")
        return None
    except Exception as e:
        st.error(f"An API error occurred: {e}")
        return None


with st.sidebar:
    st.header("⚙️ Quiz Settings")
    notes_input = st.text_area("Paste your notes or text here", height=250, key="notes_input")
    num_questions = st.slider("Number of Questions", min_value=1, max_value=15, value=5)
    difficulty = st.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
    selected_model = st.selectbox("Select AI Model (all are free)", FREE_MODELS)
    generate_button = st.button("Generate Quiz", use_container_width=True, type="primary")

for key in ['quiz_data', 'current_question', 'score', 'user_answers']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'quiz_data' else (0 if key != 'user_answers' else [])

if generate_button:
    if not st.session_state.notes_input.strip():
        st.warning("Please paste some notes before generating the quiz.")
    else:
        with st.spinner("Generating your quiz... This may take a moment."):
            quiz_data = generate_quiz_from_notes(st.session_state.notes_input, num_questions, difficulty, selected_model)
            if quiz_data and isinstance(quiz_data, list) and len(quiz_data) > 0:
                st.session_state.quiz_data = quiz_data
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.session_state.user_answers = [None] * len(quiz_data)
                st.success(f"Quiz generated with {len(quiz_data)} questions!")
                st.rerun() # Rerun to display the first question
            else:
                st.session_state.quiz_data = None
                st.error("Could not generate the quiz. Please check your model selection and try again.")

if st.session_state.quiz_data:
    q_index = st.session_state.current_question
    total_questions = len(st.session_state.quiz_data)

    if q_index < total_questions:
        question_data = st.session_state.quiz_data[q_index]
        st.header(f"Question {q_index + 1} of {total_questions}")
        st.subheader(question_data.get("question", "No question text found."))
        with st.form(key=f"question_{q_index}"):
            options = question_data.get("options", [])
            user_choice = st.radio("Choose your answer:", options, index=None)
            submit_button = st.form_submit_button("Submit Answer")
            if submit_button:
                if user_choice is not None:
                    st.session_state.user_answers[q_index] = user_choice
                    correct_answer = question_data.get("answer")
                    if user_choice == correct_answer:
                        st.session_state.score += 1; st.success("Correct! 🎉")
                    else:
                        st.error(f"Incorrect. The correct answer was: **{correct_answer}**")
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
                st.markdown(f"- **Your Answer:** {st.session_state.user_answers[i]}")
                st.markdown(f"- **Correct Answer:** {q['answer']}")
                st.divider()
        if st.button("Take a New Quiz", use_container_width=True):
            st.session_state.quiz_data = None
            st.session_state.notes_input = ""
            st.rerun()