# Smart Knowledge Hub Agent Assist Demo

Demo only. Uses browser speech recognition (may be cloud-based) and reads the Knowledge Hub REST API. Does not connect to 3CX/PEARL or capture real calls.

## Windows PowerShell

```powershell
cd voice-api-demo-updated
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 and say: "My router LOS light is red". Click Find recommended guidance.

The app selects up to three matching source records and formats their fields into readable cards. It does not invent SOPs, questions, or TT routing. If the API is unavailable or has no matching rules, it says so. Keyword-based issue classification and basic record ranking are used, not an LLM. Verify the matching rules against the authoritative source before operational use.
