"""Team Horizon • PMGT5850 classroom prototype."""
import hashlib
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import (
    APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError,
    BadRequestError, PermissionDeniedError, RateLimitError,
)
from line_art import DEFAULT_MODEL, GenerationError, ImageValidationError, generate_line_art, prepare_image

load_dotenv(Path(__file__).with_name(".env"))
st.set_page_config(page_title="Horizon | Line Drawing", page_icon="✏️", layout="wide")
st.markdown("""<style>
.block-container {max-width:1100px;padding-top:3rem;}
h1 {letter-spacing:-0.045em;}
[data-testid="stImage"] img {border-radius:10px;}
</style>""", unsafe_allow_html=True)
st.caption("TEAM HORIZON  /  PMGT5850 CAPSTONE")
st.title("From image to line art.")
st.write("Turn a photograph into a clean black-and-white editorial drawing.")
st.caption("01 Upload an image  →  02 Generate your drawing  →  03 Download the PNG")
key = os.getenv("OPENAI_API_KEY", "").strip()
if key in {"your_api_key_here", "sk-your-key-here"}:
    key = ""
model = os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
if not key:
    st.info("Setup needed: copy .env.example to .env, set OPENAI_API_KEY to your OpenAI API key, "
            "then restart the app. You can upload and preview images now; generation is enabled after setup.")
upload = st.file_uploader("Upload one image", type=["jpg", "jpeg", "png"],
                          help="JPG or PNG · up to 10 MB · up to 25 megapixels")
st.caption("Your image is sent to OpenAI only when you click Generate. Generation uses your API account.")
raw = upload.getvalue() if upload else None
identity = hashlib.sha256(raw).hexdigest() if raw else None
if st.session_state.get("source_id") != identity:
    st.session_state.source_id = identity
    st.session_state.pop("result", None)
    st.session_state.pop("prepared", None)
prepared = None
if raw is not None:
    try:
        if "prepared" not in st.session_state:
            st.session_state.prepared = prepare_image(raw)
        prepared = st.session_state.prepared
    except ImageValidationError as exc:
        st.error(str(exc))
clicked = st.button("Generate Line Drawing", type="primary", disabled=not (key and prepared))
if clicked:
    st.session_state.pop("result", None)
    try:
        with st.spinner("Creating your line drawing. This may take a few minutes…"):
            st.session_state.result = generate_line_art(prepared, key, model)
    except AuthenticationError:
        st.error("The API key was not accepted. Check OPENAI_API_KEY in .env and restart the app.")
    except PermissionDeniedError:
        st.error("Your API project cannot access this image model. Check project permissions and model access.")
    except RateLimitError:
        st.error("The API rate limit or available quota was reached. Check your API account or try again later.")
    except APITimeoutError:
        st.error("Generation timed out. The request may still have been processed. Wait before retrying.")
    except APIConnectionError:
        st.error("Could not connect to OpenAI. Check your internet connection and try again.")
    except BadRequestError:
        st.error("OpenAI could not process this request. Try a different image, or check the configured model and account access.")
    except APIStatusError:
        st.error("The image service is temporarily unavailable. Please try again later.")
    except GenerationError as exc:
        st.error(str(exc))
    except Exception:
        st.error("An unexpected error occurred. Restart the app and try again.")
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Original")
    if prepared:
        st.image(prepared, width="stretch")
        st.caption("Preview · orientation corrected and resized if needed")
    else:
        st.info("Upload a JPG or PNG to preview it here.")
with right:
    st.subheader("Line drawing")
    if st.session_state.get("result"):
        st.image(st.session_state.result, width="stretch")
        st.download_button("Download line drawing", st.session_state.result,
                           file_name="horizon-line-drawing.png", mime="image/png")
    else:
        st.info("Your generated drawing will appear here.")
st.divider()
st.caption("Team Horizon · University capstone prototype · AI results may vary. "
           "Images are held in the current session; this app does not save an image history.")
