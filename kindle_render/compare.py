"""Compare a rendered page with a reference screenshot using strict pixel equality."""
import numpy as np
from PIL import Image
from .raster import get_freetype_version

from . import __version__ as ENGINE_VERSION

def _gray(p):
    return np.array(Image.open(p).convert("L")).astype(np.int32)

def bands(a, y0=83, y1=2240):
    """Detect horizontal text ink bands between y0 and y1."""
    sub = a[y0:y1] < 250
    rows = np.where(sub.any(axis=1))[0]
    out = []
    if len(rows) == 0:
        return out
    s = q = rows[0]
    for y in rows[1:]:
        if y != q + 1:
            out.append((s + y0, q + y0))
            s = y
        q = y
    out.append((s + y0, q + y0))
    res = []
    for t, b in out:
        cols = np.where((a[t:b + 1] < 250).any(axis=0))[0]
        res.append((int(t), int(b), int(cols[0]), int(cols[-1])))

    merged = []
    for cur in res:
        if not merged:
            merged.append(cur)
            continue
        prev = merged[-1]
        gap = cur[0] - prev[1]
        if gap <= 6 and (cur[1] - prev[0] <= 60):
            merged[-1] = (prev[0], cur[1], min(prev[2], cur[2]), max(prev[3], cur[3]))
        else:
            merged.append(cur)
    return merged

def compare(ref_path, out_path, y0=83, y1=2240, diff_path=None):
    """Computes strict pixel-equality and band-level alignment metrics over y0..y1."""
    R, O = _gray(ref_path), _gray(out_path)
    rep = {
        "engine_version": ENGINE_VERSION,
        "freetype_version": get_freetype_version(),
        "compare_window_y": (y0, y1),
    }
    rb, ob = bands(R, y0, y1), bands(O, y0, y1)
    rep["ref_bands"], rep["out_bands"] = len(rb), len(ob)

    r_sub, o_sub = R[y0:y1], O[y0:y1]
    rep["bitwise_exact"] = bool(np.array_equal(r_sub, o_sub))

    d = np.abs(r_sub - o_sub)
    rep["diff_pixel_count"] = int((d > 0).sum())
    rep["max_abs_diff"] = int(d.max()) if d.size else 0
    rep["pixel_identical_percent"] = round(100.0 * float((d == 0).mean()), 4)
    rep["mean_abs_diff"] = round(float(d.mean()), 6)

    rr, oo = r_sub < 250, o_sub < 250
    inter, uni = (rr & oo).sum(), (rr | oo).sum()
    rep["ink_iou"] = round(float(inter) / max(1, uni), 4)

    rows = []
    for i, (a, b) in enumerate(zip(rb, ob)):
        rows.append(dict(
            line=i,
            ref_top=a[0], ref_bottom=a[1], out_top=b[0], out_bottom=b[1],
            dy_top=b[0] - a[0], dy_bottom=b[1] - a[1],
            ref_x=(a[2], a[3]), out_x=(b[2], b[3]),
            dx_first=b[2] - a[2], dx_last=b[3] - a[3]
        ))
    rep["lines"] = rows
    n = len(rows)
    if n:
        rep["lines_same_vertical_extent"] = sum(1 for r in rows if r["dy_top"] == 0 and r["dy_bottom"] == 0)
        rep["lines_same_last_ink_col"] = sum(1 for r in rows if r["dx_last"] == 0)
        rep["lines_last_ink_within_1px"] = sum(1 for r in rows if abs(r["dx_last"]) <= 1)
        rep["lines_same_first_ink_col"] = sum(1 for r in rows if r["dx_first"] == 0)

        ident = 0
        for a, b in zip(rb, ob):
            top, bot = min(a[0], b[0]), max(a[1], b[1]) + 1
            if np.array_equal(R[top:bot], O[top:bot]):
                ident += 1
        rep["lines_pixel_identical"] = ident

    if diff_path:
        H, W = R.shape[:2]
        diff_rgb = np.ones((H, W, 3), dtype=np.uint8) * 255
        match = (R < 250) & (O < 250)
        diff_rgb[match] = [20, 20, 20]
        ref_only = (R < 250) & (O >= 250)
        diff_rgb[ref_only] = [230, 40, 40]
        out_only = (R >= 250) & (O < 250)
        diff_rgb[out_only] = [40, 80, 230]
        Image.fromarray(diff_rgb).save(diff_path)
        rep["diff_image"] = diff_path

    return rep

def print_report(rep):
    keys = [k for k in rep if k != "lines"]
    for k in keys:
        print(f"{k}: {rep[k]}")
    bad = [r for r in rep.get("lines", []) if r["dy_top"] or r["dy_bottom"] or r["dx_first"] or r["dx_last"]]
    print(f"lines differing in extent: {len(bad)} of {len(rep.get('lines', []))}")
    for r in bad[:20]:
        print("  ", r)
