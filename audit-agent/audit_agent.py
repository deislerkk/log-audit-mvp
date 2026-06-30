import os, time, hashlib, json, requests, yaml, datetime, re

OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "http://localhost:9200")
OPENSEARCH_USER = os.environ.get("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", "admin")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "15"))

RULE_FILE = "rules.yml"
LOG_INDEX = "logs"
AUDIT_INDEX = "audit"

session = requests.Session()
session.auth = (OPENSEARCH_USER, OPENSEARCH_PASSWORD)
session.headers.update({"Content-Type":"application/json"})

def load_rules():
    with open(RULE_FILE, "r") as f:
        return yaml.safe_load(f)["rules"]

def ensure_index(index):
    url = f"{OPENSEARCH_HOST}/{index}"
    r = session.get(url)
    if r.status_code == 200:
        return
    # create minimal mapping
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp": {"type":"date"},
                "message": {"type":"text"},
                "host": {"type":"keyword"},
                "user": {"type":"keyword"}
            }
        }
    }
    session.put(url, data=json.dumps(mapping))

def parse_log_line_to_doc(line):
    # very simple kv parser for the generator format
    doc = {}
    try:
        # ISO timestamp at start
        parts = line.strip().split(" ", 1)
        ts = parts[0]
        rest = parts[1] if len(parts)>1 else ""
        doc["@timestamp"] = ts
        # find key=val pairs
        for m in re.finditer(r'(\w+)=(".*?"|\S+)', rest):
            k = m.group(1)
            v = m.group(2)
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            doc[k] = v
        # message fallback
        if "message" not in doc and rest:
            doc["message"] = rest
    except Exception:
        doc["message"] = line.strip()
    return doc

def search_logs(query):
    url = f"{OPENSEARCH_HOST}/{LOG_INDEX}/_search"
    r = session.post(url, data=json.dumps(query))
    r.raise_for_status()
    return r.json()

def index_audit(doc):
    url = f"{OPENSEARCH_HOST}/{AUDIT_INDEX}/_doc"
    r = session.post(url, data=json.dumps(doc))
    r.raise_for_status()
    return r.json()

def get_last_audit_hash():
    # get last audit entry sorted by timestamp
    url = f"{OPENSEARCH_HOST}/{AUDIT_INDEX}/_search"
    q = {"size":1,"sort":[{"@timestamp":{"order":"desc"}}]}
    r = session.post(url, data=json.dumps(q))
    if r.status_code!=200:
        return ""
    res = r.json()
    hits = res.get("hits",{}).get("hits",[])
    if not hits:
        return ""
    return hits[0]["_source"].get("hash","")

def compute_hash(prev_hash, payload):
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256((prev_hash + "|" + s).encode("utf-8")).hexdigest()
    return h

def extract_key_from_doc(doc, keyname):
    # simple extraction: expects doc to have that field (e.g., user)
    return doc.get(keyname)

def run_detection(rules):
    now = datetime.datetime.utcnow()
    for rule in rules:
        window = rule.get("sliding_window_seconds", 60)
        threshold = rule.get("threshold", 3)
        pattern = rule.get("pattern")
        per_key = rule.get("per_key", "user")
        since = (now - datetime.timedelta(seconds=window)).isoformat() + "Z"

        # search logs in window that match pattern
        q = {
            "size": 5000,
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": since}}},
                        {"match_phrase": {"message": pattern}}
                    ]
                }
            }
        }
        res = search_logs(q)
        hits = res.get("hits",{}).get("hits",[])
        # group by per_key
        buckets = {}
        for h in hits:
            src = h.get("_source",{})
            key = extract_key_from_doc(src, per_key) or "UNKNOWN"
            buckets.setdefault(key, []).append({"id": h.get("_id"), "doc": src})

        # evaluate thresholds
        for key, events in buckets.items():
            count = len(events)
            if count >= threshold:
                # check if we've already alerted for same key in recent window (naive: query audit index)
                # create audit evidence
                evidence = events
                prev_hash = get_last_audit_hash()
                audit_doc = {
                    "@timestamp": now.isoformat() + "Z",
                    "rule_id": rule.get("id"),
                    "rule_desc": rule.get("description"),
                    "key": key,
                    "count": count,
                    "evidence": evidence
                }
                h = compute_hash(prev_hash, audit_doc)
                audit_doc["prev_hash"] = prev_hash
                audit_doc["hash"] = h
                print(f"[ALERT] rule={rule.get('id')} key={key} count={count}")
                index_audit(audit_doc)
            else:
                # no alert
                pass

def main():
    print("audit-agent starting, connecting to:", OPENSEARCH_HOST)
    rules = load_rules()
    ensure_index(LOG_INDEX)
    ensure_index(AUDIT_INDEX)
    # Note: Fluent Bit writes to LOG_INDEX; this agent periodically scans LOG_INDEX
    while True:
        try:
            run_detection(rules)
        except Exception as e:
            print("error in detection:", e)
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
