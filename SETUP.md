# SETUP.md — one-time setup (do this once)

You need to do a handful of things a human has to do. After that, Claude Code handles the rest — including all the GitHub work.

Take these in order. Each is a checkpoint; don't move on until it's done.

---

## 1. Install the tools

You need three things installed on your computer: **Node.js**, **Claude Code**, and **Python**.

- **Node.js** (Claude Code runs on it): download the "LTS" version from https://nodejs.org and run the installer.
- **Claude Code**: open your terminal (Mac: "Terminal" app; Windows: "PowerShell") and run:
  ```
  npm install -g @anthropic-ai/claude-code
  ```
- **Python** (your agents run on it): download from https://python.org (get 3.11 or newer). On the Windows installer, **tick "Add Python to PATH."**

**Checkpoint:** in your terminal, these should each print a version number:
```
node --version
claude --version
python --version    (or: python3 --version on Mac)
```

> If you already have Claude Code Max, that covers the *building* — Claude Code writing your code. It does **not** pay for your agents' AI calls when they run. That's a separate free key, in step 4.

---

## 2. Create a GitHub account and sign in

GitHub is where your project lives so it's saved and shareable. You will **not** learn git commands — Claude Code does the committing and pushing for you.

- Make a free account at https://github.com if you don't have one.
- Install the GitHub CLI so Claude Code can talk to GitHub on your behalf: https://cli.github.com
- Then sign in — in your terminal run:
  ```
  gh auth login
  ```
  Choose **GitHub.com** → **HTTPS** → **login with a web browser**, and follow the prompts.

**Checkpoint:** running `gh auth status` says you're logged in.

That's the only GitHub work you do by hand. From here, "save my progress to GitHub" is just something you *ask Claude Code to do.*

---

## 3. Make the project folder and add these docs

- Make a new folder somewhere sensible, e.g. `trade-risk-agent`.
- Put all seven `.md` files (this one plus the others) inside it.
- Open the folder in Claude Code — in your terminal:
  ```
  cd path/to/trade-risk-agent
  claude
  ```

**Checkpoint:** Claude Code starts and you can type to it. Test it:
> "List the markdown files in this folder and tell me what each one is for."

It should read the docs and answer. Now it has all your context.

---

## 4. Get a free AI key for the agents (runtime)

Your agents make AI calls when they run. Pick **one** free option (also listed in DATA-SOURCES.md → "The AI brains"):

- **Groq** (easiest, fast, generous free tier): https://console.groq.com — sign up, create an API key.
- **Google Gemini** (also free tier): https://aistudio.google.com/apikey

Copy the key somewhere safe for the next step. (Limits and terms change — glance at the current free-tier details when you sign up.)

---

## 5. Store the key safely — never commit it

Your key is a password. It must **never** go into GitHub.

In Claude Code, paste this:
> "Create a `.env` file for my API key and a `.gitignore` that excludes `.env`, `__pycache__/`, `.venv/`, and any local data caches. Show me the `.env` file so I can paste my key in, but never commit `.env`."

Then paste your key into the `.env` file where it shows you.

**Checkpoint:** `.gitignore` exists and lists `.env`. If you ever see `.env` about to be committed, stop.

---

## 6. Create the GitHub repo (Claude Code does this)

In Claude Code:
> "Initialise a git repository here, create a new **private** repo on my GitHub called `trade-risk-agent` using the GitHub CLI, commit the current markdown files, and push. Confirm the repo URL when done."

**Checkpoint:** it prints a GitHub URL and you can open it in your browser and see your files.

---

You're set up. Open **`BUILD-GUIDE.md`** and start Phase 1.

### The "save my work" habit
After each phase in the build guide, tell Claude Code:
> "Commit everything with a clear message describing this phase, and push to GitHub."

That's your entire version-control workflow.
