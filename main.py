import json, math, os, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]

def round2(x: float) -> float | int:
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    v = whole / 100
    return int(v) if v.is_integer() else v

def parse_iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()

def forecast_case(case: dict) -> dict:
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    p1 = max(1.0, float(first["viewers"])) if first else 1.0
    curves = []
    for c in case.get("comparables", []):
        d_str = c.get("day_start")
        if not d_str or "hourly" not in c: continue
        try:
            d_start = parse_iso(d_str)
        except Exception: continue
        h_map = {}
        for pt in c.get("hourly", []):
            try:
                t = parse_iso(pt["from"])
                diff = int(t - d_start) // 3600
                if 0 <= diff < 24: h_map[diff + 1] = pt["viewers"]
            except Exception: continue
        cp1 = h_map.get(1)
        if cp1 and cp1 > 10:
            m_dict = {h: h_map[h] / cp1 for h in range(2, 25) if h in h_map}
            if len(m_dict) >= 12:
                w = math.exp(-0.5 * ((math.log(cp1) - math.log(p1)) / 1.5) ** 2)
                curves.append((w, m_dict))
    rows = []
    for f in case["forecast"]:
        h = f["hour"]
        pts = [(w, m[h]) for w, m in curves if h in m]
        if len(pts) >= 3:
            pts.sort(key=lambda x: x[1])
            tot = sum(p[0] for p in pts)
            q_list = []
            for tau in LEVELS:
                target = tau * tot
                cur, val = 0.0, pts[0][1]
                for w, v in pts:
                    cur += w
                    if cur >= target:
                        val = v
                        break
                q_list.append(round2(p1 * val))
        else:
            sig = 0.15 * math.sqrt(h - 1)
            q_list = [round2(p1 * math.exp(z * sig)) for z in [-1.645, -0.674, 0, 0.674, 1.645]]
        for i in range(1, len(q_list)):
            if q_list[i] < q_list[i-1]: q_list[i] = q_list[i-1]
        rows.append({"hour": h, "q": q_list})
    return {"hours": rows}

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        res = forecast_case(case)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(json.dumps(res, separators=(',', ':')) + '\n', encoding='utf-8')

if __name__ == "__main__":
    main()
