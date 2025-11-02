# LeetCode Pattern Explorer

An interactive tutorial and insights dashboard for identifying LeetCode problem categories, recurring patterns, and a guided study plan. The project ships with a lightweight Flask backend and a vanilla JavaScript frontend so you can explore the data locally.

## Features

- 📊 **Category analytics** – see how problems group into core topics with difficulty distribution and dominant patterns.
- 🔍 **Pattern spotlights** – discover cross-cutting techniques and inspect example problems that use them.
- 🧭 **Guided tutorial** – follow a three-stage roadmap that goes from fundamentals to synthesizing advanced patterns.
- 💬 **Interactive Q&A agent** – ask about a topic, pattern, or difficulty level and receive tailored practice suggestions.
- 📚 **Problem catalog** – browse the curated problem list that powers the agent.

## Prerequisites

- Python 3.10 or newer
- (Optional) Access to a running [`leetcode-mcp-server`](https://github.com/jinzcdev/leetcode-mcp-server) instance if you want to ingest live problem metadata.

## Getting started

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 💡 `requirements.txt` now includes `pytest` so you can execute the automated checks shown below. If you prefer not to install testing tooling globally, install the requirements inside a virtual environment as demonstrated above.

### 2. (Optional) Connect to `leetcode-mcp-server`

If you want live data instead of the sample JSON, run the MCP server in a separate terminal as documented in [jinzcdev/leetcode-mcp-server](https://github.com/jinzcdev/leetcode-mcp-server) and export its base URL before launching the dashboard:

```bash
export LEETCODE_MCP_SERVER="http://127.0.0.1:3333"
```

With the variable in place the dashboard will pull problems from the MCP endpoint on startup (and whenever you click **Refresh insights**). If the request fails the app falls back to the bundled dataset automatically.

### 3. Run the development server

```bash
python app.py
```

The application starts on [http://127.0.0.1:5000](http://127.0.0.1:5000). Open the URL in your browser to interact with the dashboard.

While the server is running you can:

- Inspect category and pattern analytics from the local dataset.
- Use the search box to filter the problem catalog.
- Ask the agent questions such as `How should I study dynamic programming?` or `Show me hard graph problems.`
- Click **Refresh insights** to re-fetch data from the MCP server (if configured) and rebuild summaries in place.

### 4. Run automated checks

A small Pytest suite exercises the Flask endpoints so you can confirm the backend is serving valid responses:

```bash
pytest
```

You can also perform a quick syntax check to ensure the project imports cleanly:

```bash
python -m compileall .
```

Running both commands before making changes helps catch regressions early.

### 5. Extending the dataset

To analyse additional problems, append entries to `data/problems.json`. Each problem supports the following fields:

- `id`: Numerical identifier (not required to match real LeetCode IDs, but should be unique).
- `title`: Problem name.
- `url`: Direct link to the problem statement.
- `difficulty`: One of `Easy`, `Medium`, or `Hard`.
- `topic`: Primary category such as `Array`, `Graph`, or `Dynamic Programming`.
- `patterns`: Array of key techniques leveraged in the solution.
- `summary`: One-sentence explanation of the core idea.
- `key_steps`: Bullet-point breakdown for the solution approach.

Click **Refresh insights** at any time to force the backend to reload data from the MCP server (or the local JSON if you are offline). The backend automatically recalculates category distributions, pattern spotlights, and the guided tutorial each time data is reloaded.

## Project structure

```
.
├── app.py               # Flask application with analysis endpoints
├── data/
│   └── problems.json    # Curated LeetCode problem sample used for insights
├── static/
│   ├── app.js           # Frontend logic fetching data and rendering UI
│   ├── index.html       # Main dashboard layout
│   └── styles.css       # Styling for the interface
├── tests/
│   └── test_app.py      # Automated endpoint smoke tests
└── README.md
```

## Troubleshooting tips

- **The dashboard shows no data** – ensure `data/problems.json` exists or that the MCP server is reachable. Check the Flask logs for fetch errors.
- **`pytest` cannot import Flask** – double-check that the virtual environment is activated and `pip install -r requirements.txt` completed successfully.
- **CORS or browser errors** – the frontend is served by Flask, so load the app through `http://127.0.0.1:5000/` rather than opening `static/index.html` directly.

With these steps you can run the dashboard locally, validate the API surface, and iterate on additional insights confidently.
└── README.md
```

## Extending the dataset

To analyse additional problems, append entries to `data/problems.json`. Each problem supports the following fields:

- `id`: Numerical identifier (not required to match real LeetCode IDs, but should be unique).
- `title`: Problem name.
- `url`: Direct link to the problem statement.
- `difficulty`: One of `Easy`, `Medium`, or `Hard`.
- `topic`: Primary category such as `Array`, `Graph`, or `Dynamic Programming`.
- `patterns`: Array of key techniques leveraged in the solution.
- `summary`: One-sentence explanation of the core idea.
- `key_steps`: Bullet-point breakdown for the solution approach.

Click **Refresh insights** at any time to force the backend to reload data from the MCP server (or the local JSON if you are offline). The backend automatically recalculates category distributions, pattern spotlights, and the guided tutorial each time data is reloaded.
