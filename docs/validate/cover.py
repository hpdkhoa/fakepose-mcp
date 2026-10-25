"""The share of the view a gun and its arms fill in eye pictures, and where their centre falls (0..1 from the left
and from the top). python cover.py <folder with *.png>"""
import glob
import sys

import numpy as np
from PIL import Image

for p in sorted(glob.glob(sys.argv[1] + "/*.png")):
    a = np.asarray(Image.open(p).convert("RGB")).astype(int)
    m = np.abs(a - a[2, 2]).sum(axis=2) > 40
    ys, xs = np.nonzero(m)
    h, w = m.shape
    print(p.split("/")[-1].split("\\")[-1], "cover %.1f%%" % (100 * m.mean()),
          "centre %.2f %.2f" % (xs.mean() / w, ys.mean() / h) if len(xs) else "nothing seen")
