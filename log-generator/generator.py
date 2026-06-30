# 简单的日志生成器，持续写入 /var/log/myapp.log
import time, random, datetime, os
users = ["alice","bob","charlie","dave","eve"]
msgs = [
    "user login successful",
    "user logout",
    "failed login attempt",
    "failed login attempt: wrong password",
    "resource accessed",
    "permission denied accessing /admin"
]
log_path = "/var/log/myapp.log"
os.makedirs("/var/log", exist_ok=True)

with open(log_path, "a", buffering=1) as f:
    while True:
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        u = random.choice(users)
        # increase probability of failed login sometimes
        if random.random() < 0.15:
            msg = random.choice([m for m in msgs if "failed" in m])
        else:
            msg = random.choice(msgs)
        line = f'{ts} host=web01 user={u} message="{msg}" request_id={random.randint(1000,9999)}\n'
        f.write(line)
        time.sleep(random.uniform(0.4, 1.5))
