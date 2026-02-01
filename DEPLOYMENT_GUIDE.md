# Deployment Guide (Render.com)

This guide shows you how to deploy your Wasl API for free on **Render**.

## 1. Prepare Your Project
1.  **Requirements File**: I have created a `requirements.txt` file in your main folder. This tells the cloud which libraries to install.
2.  **Git Repository**: You need to have your code on GitHub.
    *   If you haven't initialized git yet:
        ```bash
        git init
        git add .
        git commit -m "Initial commit for Wasl API"
        # Create a new repo on GitHub.com and follow instructions to push:
        git branch -M main
        git remote add origin https://github.com/YOUR_USERNAME/wasl-api.git
        git push -u origin main
        ```

## 2. Deploy on Render
1.  Go to [dashboard.render.com](https://dashboard.render.com) and sign up/login.
2.  Click **New +** and select **Web Service**.
3.  Connect your GitHub account and select the `wasl-api` repository.
4.  **Configure the Service**:
    *   **Name**: `wasl-api` (or any name)
    *   **Region**: Frankfurt (or nearest to you)
    *   **Branch**: `main`
    *   **Runtime**: `Python 3`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `uvicorn wasl_ai.src.api:app --host 0.0.0.0 --port $PORT`
    *   **Instance Type**: Free

## 3. Environment Variables (Critical!)
Scroll down to the **Environment Variables** section on the Render setup page. You MUST add your API Key here, or the app will fail.

*   Key: `OPENROUTER_API_KEY`
*   Value: `sk-or-your-key-here` (Paste the one from your `.env` file)

## 4. Finish
Click **Create Web Service**.
Render will build your app. It might take 2-3 minutes.
Once done, you will see a URL like: `https://wasl-api.onrender.com`.

**Share this URL with your Flutter developer!**
They should use: `https://wasl-api.onrender.com/resume/parse`
