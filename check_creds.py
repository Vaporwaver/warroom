import json
import os

try:
    if os.path.exists("google_vision_creds.json"):
        with open("google_vision_creds.json", "r", encoding="utf-8") as f:
            content = f.read()
        print(f"File size: {len(content)} characters.")
        
        info = json.loads(content)
        pk = info.get("private_key", "")
        print(f"Private key length: {len(pk)}")
        print(f"Starts with: {repr(pk[:40])}")
        print(f"Ends with: {repr(pk[-40:])}")
        
        # Check for double escaped newlines or literal \n
        if "\\n" in pk:
            print("Found double-escaped newlines (\\n). Fixing...")
            info["private_key"] = pk.replace("\\n", "\n")
            with open("google_vision_creds.json", "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
            print("Fixed file saved successfully.")
        else:
            print("No double-escaped newlines found.")
            
        # Try loading
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(info)
        print("Success! Credentials loaded successfully.")
    else:
        print("google_vision_creds.json does not exist.")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
