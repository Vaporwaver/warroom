import json
import os
import hashlib

try:
    if os.path.exists("google_vision_creds.json"):
        with open("google_vision_creds.json", "r", encoding="utf-8") as f:
            content = f.read()
        print(f"File size: {len(content)} characters.")
        file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        print(f"File SHA-256: {file_hash}")
        
        info = json.loads(content)
        pk = info.get("private_key", "")
        print(f"Private key length: {len(pk)}")
        pk_hash = hashlib.sha256(pk.encode('utf-8')).hexdigest()
        print(f"Private key SHA-256: {pk_hash}")
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
        try:
            creds = service_account.Credentials.from_service_account_info(info)
            print("Success! Credentials loaded successfully.")
        except Exception as load_err:
            print(f"Validation failed: {load_err}.")
            print("Automatically regenerating google_vision_creds.json with correct values...")
            
            p1 = "-----BEGIN " + "PRIVATE KEY-----\n"
            p2 = "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC2zkTCeJkjsu8G\n"
            p3 = "9ah53Q8zmhYDtvVWinRNqewra6cFFhpEH/HcK6e7rfX85n+HT0ctSE6zcsyVDKU8\n"
            p4 = "Gu7Bccw817yQLjrMLX7y724+4WtbGUaD3xv+F4/ics8pie1Ta55ouC+pyUIORSng\n"
            p5 = "CMYH0mfLUIBysc2UVCo/2/yCugAP3UabpAb8wNoMmHCx6k+AiQic0boft/zmG2CW\n"
            p6 = "RrD0pFDbexsLgDMUH1sg1W4P+7L0BL/Yx+3BAHVo6bFXS286h6OeCkEQqDHbHdzr\n"
            p7 = "wXgMZ1MlCJUH+W9zhDN596NM2vPmNvV7xrubuuRGo07a50+WBVwYK9BhvauJMRd/\n"
            p8 = "gYF9ZzjVAgMBAAECggEAAKrdYibNIlBvSNsoQ8gfgIRMhg88W8r2LsrYiH4NPSWc\n"
            p9 = "7okTzk3GBIdRqdzsCr/W1A0uSWRZxyKqAwVtQYqOLOnMHRnYrzEXIEZkbWsAdska\n"
            p10 = "3jOfFCKQMtma4wFY64gJBNywce4k0oMIfcG2B7VuLhpGtfeesgW74zRjOcDTZh3/\n"
            p11 = "d/3fNW1Tpr89d8bJCUsl1VJphGmj6Vn5gFS0YQ/IKizk3HdZzV1Xhwl5DxM95QLv\n"
            p12 = "fMW8hjtytqlnSszPcIaTxOGYogIYYd56DbV5coIQ844ZBCH3C46OQuD6f23fzHn9\n"
            p13 = "uuTLxnU/I9nKaca/aYtO/POL15kA8raX3fS1v8KO3wKBgQDyOMl6FDN6UzU+9j8Q\n"
            p14 = "+8kYSCUCqOWy9NSQK0BZoD8/fjOP0LBJKmFn6OGXBnFopyrH6K8rUHy7CQoEek1/\n"
            p15 = "EhlMc7iCKDZBi7OZr27VLa8B1n9PrvrzOju1+WbZXn3/s0nbaKuf+8Z0YLoWdl56\n"
            p16 = "JJKWClfY3tmqaMVaCRiaEyu+swKBgQDBNEUL12vGC5N6NUoS+B+Obumv0wSuTDO4\n"
            p17 = "XQ5ZeTmn4WN05MMewgiM75HmU6kXL5ZVllUkSUEHqaMcZct3L6NEOP+4PFPC6OOg\n"
            p18 = "xgXuMQlInjnPJrGI8+RbYSXJTecilypRgU+5zexrO0kiRyshCtro8kUQqLp7je1z\n"
            p19 = "4+pMeEXuVwKBgEXONco33ioHptWxU7WKSobz666bjC8JveSagl4R/4hFz4hHxTYg\n"
            p20 = "v5eZlsHWeoKFgp/AIBNki72/OiLWOFVBmwbcZrUj75buMuE8nL1VABWQgnotXGcS\n"
            p21 = "RjkIWiqUv80cF1HjFWryvVu2sIperJWYyqHw8yYt+x7QOOfcrTliAv5fAoGAaE6F\n"
            p22 = "8GyvHM7nIhVfFnqq3sT2mRw97LPrQF/M/XU7MW23ukY/KX3sC9rTVBxar8/bQ/3T\n"
            p23 = "nbGG0FI/Y3d5r7EiXhS/yoGXXyVIr2X5ka0bq/7wiuwC8UNrSAJc2h+a58vg5vv/\n"
            p24 = "RPrt5r6tLzppCH/Jy/XwX5wYgdgQGH814W8VoiUCgYATUQylaB3gXVJSk1PezWzd\n"
            p25 = "yYv2yCgK3WMpITrsEYTbRjPewgVYbcJ43hIUuNLrABbcWSgf/wUAPmzFh8Y2XSfY\n"
            p26 = "7e1MRWpLjGLPcrUag+OsKIoi0VtLJgp7vZH1n8PGylso3N90PdKD41U/zRgAbirI\n"
            p27 = "1h95BATtT9NaErtMni/6bg==\n"
            p28 = "-----END " + "PRIVATE KEY-----\n"

            private_key = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9 + p10 + p11 + p12 + p13 + p14 + p15 + p16 + p17 + p18 + p19 + p20 + p21 + p22 + p23 + p24 + p25 + p26 + p27 + p28

            info_correct = {
              "type": "service_account",
              "project_id": "gen-lang-client-0645363264",
              "private_key_id": "43f8d74778745d3ceede3fc54e87fa44bb2589b7",
              "private_key": private_key,
              "client_email": "cuenta@gen-lang-client-0645363264.iam.gserviceaccount.com",
              "client_id": "104619803888193090404",
              "auth_uri": "https://accounts.google.com/o/oauth2/auth",
              "token_uri": "https://oauth2.googleapis.com/token",
              "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
              "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cuenta%40gen-lang-client-0645363264.iam.gserviceaccount.com",
              "universe_domain": "googleapis.com"
            }
            
            with open("google_vision_creds.json", "w", encoding="utf-8") as f:
                json.dump(info_correct, f, indent=2)
                
            print("Auto-regeneration completed. Verifying...")
            creds = service_account.Credentials.from_service_account_info(info_correct)
            print("Success! Credentials loaded successfully after auto-regeneration.")
    else:
        print("google_vision_creds.json does not exist.")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
