"""Record every decision the fly makes in a short game, with the brain numbers behind it.

    python trace_episode.py              # 40 s, seed 0 -> evidence/episode_trace.jsonl

One JSON line per decision tick in which a ball was visible: game time, what each eye saw
(Hz), what the brain table returned (Giant Fibre, MDN, left/right descending-neuron totals,
threat side), and what the fly then did. Replaying a line through Brain.decide() reproduces it.
"""
import argparse
import json
import os

from sim import Brain, World

HERE = os.path.dirname(os.path.abspath(__file__))


class Traced(World):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.trace = []

    def _decide(self):
        j0 = self.stats["jumps"]
        super()._decide()
        if self.hz_l == 0 and self.hz_r == 0:
            return
        o = self.last_out
        action = "jump" if self.stats["jumps"] > j0 else "backwards" if self.backing else "none"
        if action == "jump":
            action = "jump_right" if o["steer"] >= 0 else "jump_left"
        self.trace.append({"t": round(self.t, 3), "left_eye_Hz": round(self.hz_l, 2), "right_eye_Hz": round(self.hz_r, 2),
                           "giant_fibre_Hz": round(o["gf"], 2), "mdn_Hz": round(o["mdn"], 2),
                           "descending_left_Hz": round(o["left"], 1), "descending_right_Hz": round(o["right"], 1),
                           "threat_side": "left" if o["steer"] > 0 else "right" if o["steer"] < 0 else "none",
                           "action": action})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    b = Brain()
    assert b.real, "needs fly_table.pkl"
    w = Traced(brain=b, policy="fly", seed=args.seed)
    for _ in range(int(args.seconds * 60)):
        w.step(1 / 60)
    os.makedirs(os.path.join(HERE, "evidence"), exist_ok=True)
    path = os.path.join(HERE, "evidence", "episode_trace.jsonl")
    with open(path, "w", encoding="utf8") as f:
        f.write(json.dumps({"header": True, "table_sha256": b.sha, "policy": "fly", "seed": args.seed,
                            "seconds": args.seconds, "stats": w.stats}) + "\n")
        for r in w.trace:
            f.write(json.dumps(r) + "\n")
    jumps = sum(r["action"].startswith("jump") for r in w.trace)
    print(f"{len(w.trace)} decisions, {jumps} brain-triggered jumps, stats {w.stats} -> {path}")


if __name__ == "__main__":
    main()
