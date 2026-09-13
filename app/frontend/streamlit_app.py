import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv
from math_formatting import normalize_math


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Statistics Practice", page_icon="📊")
st.title("Statistics Practice")

st.session_state.setdefault("problems", [])
st.session_state.setdefault("results", {})
st.session_state.setdefault("hints_shown", {})
st.session_state.setdefault("score", {"correct": 0, "attempted": 0})


def reset_practice() -> None:
    for key in list(st.session_state):
        if key.startswith(("answer_", "check_", "hint_")):
            st.session_state.pop(key, None)
    st.session_state.problems = []
    st.session_state.results = {}
    st.session_state.hints_shown = {}
    st.session_state.score = {"correct": 0, "attempted": 0}


def api_error_message(error: requests.HTTPError, fallback: str) -> str:
    if error.response is not None:
        try:
            data = error.response.json()
            detail = data.get("detail") if isinstance(data, dict) else None
            if isinstance(detail, str) and detail.strip():
                return detail
        except ValueError:
            pass
    return fallback


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
    st.button("New Set", on_click=reset_practice)

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
                   or not isinstance(p.get("question"), str)
                   or not isinstance(p.get("hints"), list)
                   or not all(isinstance(hint, str) for hint in p["hints"]) for p in problems):
                raise ValueError("Invalid problem data")
            if len({p["id"] for p in problems}) != len(problems):
                raise ValueError("Duplicate problem IDs")
        except requests.Timeout:
            st.error("Problem generation timed out. Please try again.")
        except requests.HTTPError as exc:
            st.error(api_error_message(exc, "Couldn't generate problems. Please try again."))
        except (requests.RequestException, ValueError, KeyError, TypeError):
            st.error("Couldn't generate problems. Make sure the backend is running and try again.")
        else:
            reset_practice()
            st.session_state.problems = problems

if not st.session_state.problems:
    st.info("Choose a topic and difficulty in the sidebar, then select Generate Problems.")

for index, problem in enumerate(st.session_state.problems, start=1):
    with st.container():
        st.subheader(f"Problem {index}")
        st.markdown(normalize_math(problem["question"]))
        problem_id = problem["id"]
        checked = problem_id in st.session_state.results
        answer = st.text_input("Your answer", key=f"answer_{problem_id}", disabled=checked)
        with st.expander("Hint"):
            hints = problem.get("hints", [])
            shown = st.session_state.hints_shown.get(problem_id, 0)
            if st.button("Next hint", key=f"hint_{problem_id}", disabled=shown >= len(hints)):
                shown += 1
                st.session_state.hints_shown[problem_id] = shown
                st.rerun()
            for hint in hints[:shown]:
                st.markdown(normalize_math(hint))
            if not hints:
                st.caption("No hints available for this problem.")
            elif shown == len(hints):
                st.caption("All hints shown.")
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
                            st.error('This problem is no longer available. Select "New Set" in the sidebar, then generate problems.')
                        else:
                            st.error(api_error_message(exc, "Couldn't check your answer. Please try again."))
                    except requests.Timeout:
                        st.error("Answer checking timed out. Please try again.")
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
                st.success(normalize_math(result["feedback"]))
            else:
                st.error(normalize_math(result["feedback"]))
            st.markdown("**Worked solution**")
            st.markdown(normalize_math("\n\n".join(result["solution_steps"])))
            st.markdown("**Final answer**")
            st.markdown(normalize_math(result["final_answer"]))

st.sidebar.metric(
    "Score", f"{st.session_state.score['correct']}/{st.session_state.score['attempted']}"
)
