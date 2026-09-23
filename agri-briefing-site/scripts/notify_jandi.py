"""Notify JANDI only after Pages deployment succeeds."""
import json, logging, os, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from briefing_lib import jandi_payload

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
ROOT = Path(__file__).resolve().parents[1]

def load_local_env() -> None:
    """Load local-only key/value settings; deployment always supplies GitHub Secrets."""
    env_file = ROOT / ".env"
    if not env_file.exists(): return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

def main() -> None:
    load_local_env()
    webhook, site_url = os.getenv("JANDI_NEWS_WEBHOOK_URL"), os.getenv("SITE_URL")
    if not webhook or not site_url:
        logging.warning("JANDI_NEWS_WEBHOOK_URL or SITE_URL is absent; notification skipped")
        return
    date = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    requested_file = os.getenv("BRIEFING_FILE", "")
    source = (ROOT / requested_file).resolve() if requested_file else ROOT / "data" / f"{date}.json"
    if ROOT not in source.parents:
        raise ValueError("BRIEFING_FILE must point inside the project")
    if not source.exists(): logging.info("No briefing generated today; notification skipped"); return
    payload = jandi_payload(json.loads(source.read_text(encoding="utf-8")), site_url)
    request = urllib.request.Request(webhook, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Accept": "application/vnd.tosslab.jandi-v2+json", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response: logging.info("JANDI response status=%s", response.status)
    except urllib.error.HTTPError as exc:
        logging.error("JANDI HTTP failure status=%s message=%s", exc.code, exc.read().decode("utf-8", "replace")); raise
    except urllib.error.URLError as exc:
        logging.error("JANDI connection failure: %s", exc.reason); raise

if __name__ == "__main__": main()
