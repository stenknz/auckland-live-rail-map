import os

def test_api_key_not_in_frontend_dist():
    # Ensure the subscription key is never baked into the frontend bundle.
    key = None
    for line in open(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")):
        if line.startswith("AT_SUBSCRIPTION_KEY="):
            key = line.strip().split("=", 1)[1]
            break
    if not key or key == "CHANGEME":
        return
    dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
    if not os.path.isdir(dist):
        return
    for root, _, files in os.walk(dist):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                content = open(path, "rb").read()
            except Exception:
                continue
            assert key.encode() not in content, f"API key found in {path}"
