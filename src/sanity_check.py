"""Run the handbook's sanity checks: python src/sanity_check.py"""
from flybrain import load_brain

b = load_brain()
print(f"{b.N:,} neurons, {b.W.nnz:,} connections")
for name in ["sugar", "bitter", "looming", "mn9", "giant_fibre", "mdn"]:
    print(f"{name:12s} {len(getattr(b, name)):4d} neurons")

def run(inputs, W=None):
    c = b.simulate(inputs, W=W)
    return c, b.rate(c, b.mn9), b.rate(c, b.giant_fibre)

c, _, _ = run([])
print("nothing   -> active neurons:", int((c > 0).sum()), "(expect 0)")
_, mn9, _ = run([(b.sugar, 200)])
print("sugar     -> mn9 Hz:", mn9, "(expect high)")
_, mn9b, _ = run([(b.sugar, 200), (b.bitter, 200)])
print("sugar+bit -> mn9 Hz:", mn9b, "(expect much lower)")
_, _, gf = run([(b.looming, 150)])
print("looming   -> giant fibre Hz:", gf, "(expect high)")
c1 = b.simulate([(b.looming, 150)])
c2 = b.simulate([(b.looming, 150)], W=b.lesion(b.giant_fibre))
print("looming active neurons: intact", int((c1 > 0).sum()), "vs giant fibre lesioned", int((c2 > 0).sum()),
      "(just shows the lesion changes the network; not a pass/fail)")
