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

## LOS guidance cards update

For a simulated LOS Red customer report the UI shows only the matching operational rule's explicitly named troubleshooting steps, customer questions, TT routing and any additional source fields. Missing values are marked as unavailable rather than guessed. The matching is keyword-based, not an LLM. The actual production Knowledge Hub JSON schema has not been verified during this change; validate the output with a known real record before any operational use.
