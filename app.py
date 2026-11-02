# import json
# import gradio as gr
# import torch
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# MODEL_ID = "moizshah956/bawdicsoft_agent"

# tok = AutoTokenizer.from_pretrained(MODEL_ID)
# mdl = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID).eval()

# def build_context(messages):
#     turns = []
#     for m in messages[-6:]:
#         role = "agent" if m["role"] in ("assistant", "agent") else "visitor"
#         turns.append(f"{role}: {m['content']}")
#     return " | ".join(turns) if turns else "[conversation start]"

# def chat(user_type, user_name, user_interests, page, messages_json):
#     messages = json.loads(messages_json)
#     text = (
#         f"user_type: {user_type or 'unknown'} | "
#         f"user_name: {user_name or 'none'} | "
#         f"user_interests: {user_interests or 'none'} | "
#         f"page: {page or '/'} | "
#         f"context: {build_context(messages)}"
#     )
#     ids = tok(text, return_tensors="pt", truncation=True, max_length=512)
#     with torch.no_grad():
#         out = mdl.generate(**ids, max_new_tokens=150, num_beams=1,
#                            no_repeat_ngram_size=2, do_sample=False)
#     return tok.decode(out[0], skip_special_tokens=True).strip()

# demo = gr.Interface(
#     fn=chat,
#     inputs=[
#         gr.Textbox(label="user_type"),
#         gr.Textbox(label="user_name"),
#         gr.Textbox(label="user_interests"),
#         gr.Textbox(label="page"),
#         gr.Textbox(label="messages_json"),
#     ],
#     outputs=gr.Textbox(label="reply"),
#     api_name="chat",
# )
# demo.launch()

# Fix the asyncio cleanup warning on Hugging Face Spaces.
import asyncio.base_events as _base_events


def _patch_asyncio_event_loop_cleanup():
    original_del = getattr(_base_events.BaseEventLoop, "__del__", None)

    if original_del is None:
        return

    if getattr(original_del, "_spaces_app_patched", False):
        return

    def patched_del(self):
        try:
            original_del(self)
        except ValueError as exc:
            if str(exc) != "Invalid file descriptor: -1":
                raise

    patched_del._spaces_app_patched = True
    _base_events.BaseEventLoop.__del__ = patched_del


_patch_asyncio_event_loop_cleanup()


import re
import json
import gradio as gr
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_ID = "moizshah956/bawdicsoft_agent"

tok = AutoTokenizer.from_pretrained(MODEL_ID)
mdl = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID).eval()


# ---------- COMPANY FACTS (edit anytime) ----------
COUNTRIES_ANSWER = (
    "We serve clients in 15+ countries, including the USA, UK, Canada, "
    "UAE, and Australia. Our head office is in Karachi, Pakistan, and we "
    "work with teams across time zones. Where is your business based?"
)

COUNTRY_NAMES = {
    "united states": "the USA", "usa": "the USA", "america": "the USA",
    "united kingdom": "the UK", "uk": "the UK", "england": "the UK", "britain": "the UK",
    "canada": "Canada",
    "uae": "the UAE", "dubai": "the UAE", "emirates": "the UAE",
    "australia": "Australia",
}


def find_country(t):
    for name, label in COUNTRY_NAMES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", t):
            return label
    return None


def find_company_fact(text):
    t = text.lower()
    country = find_country(t)

    # visitor is telling us where THEY are ("my business is based in uk")
    about_self = re.search(
        r"\b(based in|located in|we are in|we're in|i am in|i'm in|i am from|i'm from|"
        r"we are from|we're from|live in|my business|my company|our company|our business)\b", t)
    if country and about_self:
        return (f"Great, we work with clients in {country} and across 15+ countries, "
                "so time zones are no problem. What are you looking to build?")

    # visitor is asking which countries we serve
    asks_countries = re.search(
        r"\b(countr(y|ies)|worldwide|global|international|overseas|abroad)\b", t)
    asks_about_country = country and re.search(
        r"\b(do you|can you|have you|you work|you serve|you have|clients?|customers?)\b", t)
    if asks_countries or asks_about_country:
        return COUNTRIES_ANSWER

    return None
# --------------------------------------------------


# ---------- HOLOVOX KNOWLEDGE (edit anytime) ----------
HOLOVOX_WORDS = ["holovox", "holo vox", "holo-vox", "holo assist", "holoassist"]

HOLOVOX_OVERVIEW = (
    "HoloVox is an AI-first alternative to Zoom that we built, centered on "
    "\"Holo Assist\", an AI assistant that gives you real-time insights, live "
    "summaries, and meeting briefs. It also has an in-meeting AI chatbot for "
    "instant Q&A and context retrieval, and a 360-degree presence feature for a "
    "more immersive meeting experience. What would you like to know more about?"
)

HOLOVOX_TOPICS = [
    {
        "keywords": ["holo assist", "holoassist", "assistant", "assist"],
        "answer": "Holo Assist is the AI assistant at the heart of HoloVox. During a meeting it delivers real-time insights, live summaries, and meeting briefs, so nobody has to scramble to take notes. Want to know about the in-meeting chatbot too?",
    },
    {
        "keywords": ["summary", "summaries", "summarize", "brief", "briefs", "notes", "minutes", "recap"],
        "answer": "HoloVox generates live summaries while the meeting is running, and meeting briefs so everyone has the key context. That means less manual note-taking and a quick catch-up for anyone who joins late.",
    },
    {
        "keywords": ["chatbot", "chat bot", "q&a", "question", "retrieval", "context"],
        "answer": "HoloVox has an in-meeting AI chatbot for instant Q&A and context retrieval. You can ask about something discussed earlier without interrupting the call. Do you want something like this for your own product?",
    },
    {
        "keywords": ["360", "presence", "immersive", "3d", "hologram", "holographic", "experience"],
        "answer": "HoloVox includes a 360-degree presence feature that makes meetings feel more immersive than a standard video call. Interested in a similar experience for your platform?",
    },
    {
        "keywords": ["zoom", "teams", "google meet", "alternative", "compare", "different", "better", "competitor"],
        "answer": "HoloVox is an AI-first alternative to Zoom. Where traditional tools mostly carry video and audio, HoloVox adds real-time insights, live summaries, meeting briefs, an in-meeting AI chatbot, and 360-degree presence. What are you comparing it for?",
    },
    {
        "keywords": ["build", "similar", "custom", "develop", "cost", "price", "pricing", "timeline", "quote"],
        "answer": "Yes, we can build a custom product like HoloVox for you, with AI features suited to your use case. Pricing and timeline depend on scope, and we usually start with a 30-60 day pilot. Drop your email and BawdicSoft Team will reach out with details.",
    },
]


def find_fact(text, history=""):
    t = text.lower()
    h = history.lower()

    mentioned_now = any(w in t for w in HOLOVOX_WORDS)
    mentioned_before = any(w in h for w in HOLOVOX_WORDS)

    if not (mentioned_now or mentioned_before):
        return None

    best, best_hits = None, 0
    for topic in HOLOVOX_TOPICS:
        hits = sum(1 for k in topic["keywords"] if k in t)
        if hits > best_hits:
            best, best_hits = topic, hits

    if best:
        return best["answer"]
    if mentioned_now:
        return HOLOVOX_OVERVIEW
    return None
# ------------------------------------------------------



def get_message_text(message):
    """Safely extract message text from different message formats."""
    if not isinstance(message, dict):
        return str(message) if isinstance(message, str) else ""

    value = message.get("content", message.get("text", ""))

    # Handle content represented as a list of text blocks.
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(parts).strip()

    return value.strip() if isinstance(value, str) else ""


def build_context(messages):
    turns = []

    for message in messages[-6:]:
        if not isinstance(message, dict):
            continue

        content = get_message_text(message)
        if not content:
            continue

        role = (
            "agent"
            if message.get("role") in ("assistant", "agent")
            else "visitor"
        )
        turns.append(f"{role}: {content}")

    return " | ".join(turns) if turns else "[conversation start]"


def chat(user_type, user_name, user_interests, page, messages_json):
    try:
        messages = json.loads(messages_json or "[]")
    except (json.JSONDecodeError, TypeError):
        messages = []

    if not isinstance(messages, list):
        messages = []

    last_message = ""
    for message in reversed(messages):
        last_message = get_message_text(message)
        if last_message:
            break

    # 1. Company facts
    company = find_company_fact(last_message)
    if company:
        return company

    # 2. HoloVox knowledge
    history = " ".join(
        get_message_text(message)
        for message in messages[-5:-1]
        if isinstance(message, dict)
    )

    fact = find_fact(last_message, history)
    if fact:
        return fact

    # 3. Trained model
    text = (
        f"user_type: {user_type or 'unknown'} | "
        f"user_name: {user_name or 'none'} | "
        f"user_interests: {user_interests or 'none'} | "
        f"page: {page or '/'} | "
        f"context: {build_context(messages)}"
    )

    ids = tok(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )

    with torch.no_grad():
        out = mdl.generate(
            **ids,
            max_new_tokens=150,
            num_beams=1,
            no_repeat_ngram_size=2,
            do_sample=False,
        )

    return tok.decode(out[0], skip_special_tokens=True).strip()



demo = gr.Interface(
    fn=chat,
    inputs=[
        gr.Textbox(label="user_type"),
        gr.Textbox(label="user_name"),
        gr.Textbox(label="user_interests"),
        gr.Textbox(label="page"),
        gr.Textbox(label="messages_json"),
    ],
    outputs=gr.Textbox(label="reply"),
    api_name="chat",
)
demo.launch()