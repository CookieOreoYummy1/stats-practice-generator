import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Statistics Practice", page_icon="📊")
st.title("Statistics Practice")

st.session_state.setdefault("problems", [])
st.session_state.setdefault("results", {})
st.session_state.setdefault("hints_shown", {})
st.session_state.setdefault("score", {"correct": 0, "attempted": 0})


@st.cache_data(ttl=300, show_spinner=False)
def load_topics(backend_url: str) -> list[dict]:
    response = requests.get(f"{backend_url}/api/topics", timeout=10)
    response.raise_for_status()
    topics = response.json()["topics"]
    if not isinstance(topics, list) or not topics:
        raise ValueError("No topics available")
    if any(not isinstance(t, dict) or not isinstance(t.get("id"), str)
           or not isinstance(t.get("display_name"), str) for t in topics):
        raise ValueError("Invalid topic data")
    return topics


with st.sidebar:
    st.header("Practice settings")
    try:
        topics = load_topics(BACKEND_URL)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        topics = []
        st.error("Couldn't load topics. Make sure the backend is running, then retry.")
        if st.button("Retry loading topics"):
            st.rerun()

    topic_names = {topic["id"]: topic["display_name"] for topic in topics}
    topic = st.selectbox(
        "Topic", options=list(topic_names), format_func=topic_names.get,
        disabled=not topics,
    )
    difficulty = st.radio("Difficulty", ["easy", "medium", "hard"], format_func=str.title)
    count = st.slider("Number of problems", min_value=1, max_value=5, value=1)
    generate = st.button("Generate Problems", type="primary", disabled=not topics)

if generate:
    with st.spinner("Generating problems..."):
        try:
            # Allow time for the backend's bounded generation retries.
            response = requests.post(
                f"{BACKEND_URL}/api/generate",
                json={"topic": topic, "difficulty": difficulty, "count": count},
                timeout=(10, 180),
            )
            response.raise_for_status()
            problems = response.json()["problems"]
            if not isinstance(problems, list) or len(problems) != count:
                raise ValueError("Unexpected problem count")
            if any(not isinstance(p, dict) or not isinstance(p.get("id"), str)
                   or not isinstance(p.get("question"), str) for p in problems):
                raise ValueError("Invalid problem data")
            if len({p["id"] for p in problems}) != len(problems):
                raise ValueError("Duplicate problem IDs")
        except requests.Timeout:
            st.error("Problem generation timed out. Please try again.")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            st.error("Couldn't generate problems. Make sure the backend is running and try again.")
        else:
            for old_problem in st.session_state.problems:
                st.session_state.pop(f"answer_{old_problem['id']}", None)
            st.session_state.problems = problems
            st.session_state.results = {}
            st.session_state.hints_shown = {}
            st.session_state.score = {"correct": 0, "attempted": 0}

if not st.session_state.problems:
    st.info("Choose a topic and difficulty in the sidebar, then select Generate Problems.")

for index, problem in enumerate(st.session_state.problems, start=1):
    with st.container():
        st.subheader(f"Problem {index}")
        st.markdown(problem["question"])
        problem_id = problem["id"]
        checked = problem_id in st.session_state.results
        answer = st.text_input("Your answer", key=f"answer_{problem_id}", disabled=checked)
        if st.button("Check Answer", key=f"check_{problem_id}", disabled=checked):
            if not answer.strip():
                st.error("Enter an answer before checking.")
            else:
                with st.spinner("Checking your answer..."):
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/api/check",
                            json={"problem_id": problem_id, "user_answer": answer},
                            timeout=(10, 180),
                        )
                        response.raise_for_status()
                        result = response.json()
                        if (not isinstance(result, dict)
                            or type(result.get("correct")) is not bool
                            or not isinstance(result.get("feedback"), str)
                            or not isinstance(result.get("final_answer"), str)
                            or not isinstance(result.get("solution_steps"), list)
                            or not all(isinstance(step, str) for step in result["solution_steps"])):
                            raise ValueError("Invalid answer-check response")
                    except requests.HTTPError as exc:
                        if exc.response is not None and exc.response.status_code == 404:
                            st.error("This problem is no longer available. Generate a new set of problems.")
                        else:
                            st.error("Couldn't check your answer. Please try again.")
                    except (requests.RequestException, ValueError):
                        st.error("Couldn't check your answer. Please try again.")
                    else:
                        st.session_state.results[problem_id] = result
                        st.session_state.score["attempted"] += 1
                        st.session_state.score["correct"] += int(result["correct"])
                        st.rerun()

        if problem_id in st.session_state.results:
            result = st.session_state.results[problem_id]
            if result["correct"]:
                st.success(result["feedback"])
            else:
                st.error(result["feedback"])
            st.markdown("**Worked solution**")
            for step in result["solution_steps"]:
                st.markdown(step)
            st.markdown("**Final answer**")
            st.markdown(result["final_answer"])

st.sidebar.metric(
    "Score", f"{st.session_state.score['correct']}/{st.session_state.score['attempted']}"
)
