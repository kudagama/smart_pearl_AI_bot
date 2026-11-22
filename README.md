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

## 4G search and package cards

Search for **4G** to see the verified 4G LTE prepaid recharge rules (direct channels and third-party/bank channels), their routing, applicable channels, required transaction information and advice in readable cards.

**4G package rental/pricing is not supplied by the existing Smart Knowledge Hub API dataset.** The UI explicitly indicates this rather than showing unrelated telemetry or inventing an amount. To display real 4G data-package prices, the Knowledge Hub team must publish a 4G packages collection or documented endpoint that includes package names, quotas, validity and prices. Trio prices remain separate and are shown as actual API-sourced price cards when querying Trio packages.

The frontend uses the existing browser microphone and manual search. Only demo/synthetic conversations should be used without approved customer audio capture. Tests: `python -m unittest test_app.py`.

## 4G Prepaid / Postpaid dashboard

Search `4G`, `4 g`, `four g` or `LTE` to open a service overview with **Overview**, **Prepaid**, **Postpaid** and **Recharge support** tabs. Prepaid/Postpaid prices, quotas and validity are rendered only from dedicated 4G/LTE data in the Knowledge Hub; 4G recharge fault advice remains separate. The currently supplied Knowledge Hub export contains recharge fault rules but **does not contain 4G package price tables**. Until a 4G packages collection is published, the interface explicitly says pricing is unavailable.

One supported shape for the Master Knowledge Hub JSON response is:

```json
{
  "collections": {
    "four_g": {
      "prepaid": [
        {"name":"Example plan","priceLkr":null,"quotaGb":null,"validityDays":null}
      ],
      "postpaid": [
        {"name":"Example rental","monthlyRentalLkr":null,"quotaGb":null}
      ]
    }
  }
}
```

These are **schema examples, not actual offerings**. Fill amounts and package details from the official 4G source only. The app also accepts top-level `four_g`, `fourG`, `4gPackages`, and similar collections.
