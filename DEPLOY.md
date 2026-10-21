# Streamlit Community Cloud deployment

1. Sign in at https://share.streamlit.io/ and connect the GitHub account that will own the project.
2. Put the project source in a GitHub repository. Upload only the files in team-horizon-deploy.zip. Never upload `.env`, `.streamlit/secrets.toml`, or a virtual environment.
3. Create an app using that repository, its actual branch, and entrypoint `app.py`.
4. Choose Python 3.11 in Advanced settings. In Secrets, configure the following privately:

```toml
OPENAI_API_KEY = "YOUR_ACTUAL_KEY"
OPENAI_IMAGE_MODEL = "gpt-image-1.5"
```

Root-level Streamlit secrets are available as environment variables. No source-code change is required.
5. Deploy and wait until the app is running. Copy the actual URL supplied by Streamlit; do not use localhost.
6. Verify access in another browser. Upload a JPG/PNG, generate one result after the API account has available quota, compare it and download the PNG.

The API quota/billing error seen locally will also affect the hosted version until the API account issue is resolved. A public app uses the owner's configured API account for visitor generations. Use hosting viewer restrictions for a limited teacher demonstration where available; review sharing before distributing the URL.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
Secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
