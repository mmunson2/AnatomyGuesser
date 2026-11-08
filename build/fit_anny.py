"""Make the female skin outline; writes female_skin.npz.

    python3 build/fit_anny.py <bp3d_dir> <hra_dir>

Needs torch, anny, scipy, trimesh and rtree (`make setup-anny`;
not the anny[smpl] extra, whose assets are non-commercial). Rerun it
when the female body's anatomy changes; build_model.py only reads the
saved mesh.

The skin is an adult female from Anny (NAVER LABS Europe, Apache 2.0 code,
CC0 MakeHuman-derived assets), fitted around the female body: the
BodyParts3D skeleton and muscles with the HRA pelvis and breasts.

  1. Pose. Her shoulders, elbows, wrists, hips, knees, ankles, eyes,
     knuckles, finger and toe joints are pulled onto ours, solving for one
     overall scale and translation and the bone rotations.
  2. Shape. With the scale fixed, her weight, muscle, proportions, cup size
     and breast firmness, the hands, feet, neck and head, and the head's
     size (the BodyParts3D male skull is bigger than her head) adjust so
     her skin encloses as much of the anatomy as it can.
  3. Shrink-wrap. Where anatomy still pokes through (a female outline on
     male muscles), the skin is pushed out just enough to cover it, with a
     smooth falloff. Elsewhere it doesn't move, and the hands and feet
     never move (see EXTREMITY_SKIN).
"""

import re
import sys
from pathlib import Path

import anny
import numpy as np
import torch
import trimesh
from scipy.sparse import coo_matrix, diags
from scipy.spatial import cKDTree

from build_model import build_parts

OUT = Path(__file__).with_name("female_skin.npz")
SAMPLES = 40000      # anatomy points the skin must enclose
MARGIN = 0.004       # metres of clearance
# Anny axes are x = left, y = posterior, z = up; ours are x = left, y = up, z = anterior.
TO_BODY = torch.tensor([[1.0, 0, 0], [0, 0, 1], [0, -1, 0]])
FIXED_PHENOTYPES = {"gender": 1.0, "age": 2 / 3}  # female, young adult
FREE_PHENOTYPES = ["muscle", "weight", "proportions", "cupsize", "firmness"]
LIMBS = re.compile(r"^(upperarm01|lowerarm01|upperleg01|lowerleg01)\.")
# Fingers and toes keep Anny's natural rest pose: rotated one by one toward a
# few averaged landmarks they crumple. The hand and foot landmarks orient the
# whole hand and foot instead. (Letting the thumb follow its own landmark
# rolls the whole hand and curls the fingers, so it stays at rest too.)
EXTREMITIES = re.compile(r"^(neck0\d|head|lowerarm02|wrist|foot)")
# Skin the shrink-wrap never moves, by Anny skinning weight. Our straight
# finger and toe bones and the forearm tendons running to the finger tips
# don't match her relaxed hands, and pushing thin fingers out to cover them
# makes lumps; some bone showing through looks better.
EXTREMITY_SKIN = re.compile(r"^(wrist|metacarpal|finger|foot|toe)")


def side(v, s):
    return v[v[:, 0] * s > 0]


def landmarks(parts):
    """Our joint centres, keyed by the Anny bone whose head sits there. A
    tuple key means the mean of those bones' heads."""
    g = lambda pid: parts[pid]
    out = {}
    for s, tag in ((1, "L"), (-1, "R")):
        hum = side(g("humerus"), s)
        out[f"upperarm01.{tag}"] = hum[hum[:, 1] > hum[:, 1].max() - 0.03].mean(0)
        out[f"lowerarm01.{tag}"] = hum[hum[:, 1] < hum[:, 1].min() + 0.02].mean(0)
        fa = side(np.concatenate([g("radius"), g("ulna")]), s)
        out[f"wrist.{tag}"] = fa[fa[:, 1] < fa[:, 1].min() + 0.015].mean(0)
        fem = side(g("femur"), s)
        top = fem[fem[:, 1] > fem[:, 1].max() - 0.05]
        out[f"upperleg01.{tag}"] = top[np.abs(top[:, 0]) < np.median(np.abs(top[:, 0]))].mean(0)
        tib = side(g("tibia"), s)
        out[f"lowerleg01.{tag}"] = np.concatenate([fem[fem[:, 1] < fem[:, 1].min() + 0.02],
                                                  tib[tib[:, 1] > tib[:, 1].max() - 0.02]]).mean(0)
        out[f"foot.{tag}"] = side(g("talus"), s).mean(0)
        out[f"eye.{tag}"] = side(g("eye"), s).mean(0)
        # Hand: knuckles are the lowest ends of the metacarpals (the thumb's
        # sits higher), the finger tips' joints just above the lowest bone,
        # and the thumb is the most lateral finger bone.
        mc = side(g("metacarpals"), s)
        out[tuple(f"finger{k}-1.{tag}" for k in range(2, 6))] = mc[mc[:, 1] < mc[:, 1].min() + 0.015].mean(0)
        ph = side(g("finger_phalanges"), s)
        band = ph[(ph[:, 1] > ph[:, 1].min() + 0.015) & (ph[:, 1] < ph[:, 1].min() + 0.035)]
        out[tuple(f"finger{k}-3.{tag}" for k in range(2, 6))] = band.mean(0)
        lateral = np.abs(ph[:, 0])
        out[f"finger1-3.{tag}"] = ph[lateral > np.percentile(lateral, 97)].mean(0)
        # Foot: the toe joints are the front ends of the metatarsals.
        mt = side(g("metatarsals"), s)
        out[tuple(f"toe{k}-1.{tag}" for k in range(1, 6))] = mt[mt[:, 2] > mt[:, 2].max() - 0.015].mean(0)
    return out


def rodrigues(v):
    th = v.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    k = v / th
    K = torch.zeros(v.shape[0], 3, 3)
    K[:, 0, 1], K[:, 0, 2], K[:, 1, 2] = -k[:, 2], k[:, 1], -k[:, 0]
    K = K - K.transpose(1, 2)
    th = th[..., None]
    return torch.eye(3) + torch.sin(th) * K + (1 - torch.cos(th)) * K @ K


def contains(mesh, pts, chunk=10000):
    return np.concatenate([mesh.contains(pts[k:k + chunk]) for k in range(0, len(pts), chunk)])


class Fit:
    def __init__(self, targets):
        self.model = anny.Anny(phenotypes="all").to(dtype=torch.float32)
        self.faces = np.asarray(self.model.faces)
        labels = self.model.bone_labels
        index = {b: i for i, b in enumerate(labels)}
        self.posed = [b for b in labels if b not in ("root", "pelvis.L", "pelvis.R", "eye.L", "eye.R")]
        self.posed_idx = [index[b] for b in self.posed]
        self.is_head = torch.tensor([b == "head" for b in self.posed])[:, None, None]
        keys = list(targets)
        groups = [[index[b] for b in (k if isinstance(k, tuple) else (k,))] for k in keys]
        width = max(len(g) for g in groups)
        # Each landmark averages up to `width` bone heads; pad by repeating.
        self.groups = torch.tensor([g + [g[0]] * (width - len(g)) for g in groups])
        self.counts = torch.tensor([len(g) for g in groups], dtype=torch.float32)
        self.pad = torch.tensor([[1.0] * len(g) + [0.0] * (width - len(g)) for g in groups])
        self.target = torch.tensor(np.array([targets[k] for k in keys]), dtype=torch.float32)
        self.angles = torch.zeros(len(self.posed), 3, requires_grad=True)
        self.logits = torch.zeros(len(FREE_PHENOTYPES), requires_grad=True)
        self.log_head = torch.zeros(1, requires_grad=True)
        self.log_scale = torch.zeros(1, requires_grad=True)
        self.shift = torch.zeros(3, requires_grad=True)

    def free(self):
        """Per vertex, 1 minus its skinning weight on the hand and foot bones."""
        held = torch.tensor([bool(EXTREMITY_SKIN.match(b)) for b in self.model.bone_labels])
        w = self.model.vertex_bone_weights * held[self.model.vertex_bone_indices]
        return 1 - w.sum(1).numpy()

    def mask(self, pattern):
        return torch.tensor([[1.0] if pattern.match(b) else [0.0] for b in self.posed])

    def phenotypes(self):
        ph = {k: 0.5 for k in self.model.phenotype_labels}
        ph.update(FIXED_PHENOTYPES)
        values = torch.sigmoid(self.logits)
        for n, k in enumerate(FREE_PHENOTYPES):
            ph[k] = values[n:n + 1]
        return ph

    def __call__(self):
        pose = torch.eye(4)[None, None].repeat(1, self.model.bone_count, 1, 1).clone()
        rot = rodrigues(self.angles)
        pose[0, self.posed_idx, :3, :3] = torch.where(self.is_head, rot * torch.exp(self.log_head), rot)
        o = self.model(pose_parameters=pose, phenotype_kwargs=self.phenotypes())
        s = torch.exp(self.log_scale)
        verts = s * (o["vertices"][0] @ TO_BODY.T) + self.shift
        heads = s * (o["bone_poses"][0, :, :3, 3] @ TO_BODY.T) + self.shift
        joints = (heads[self.groups] * self.pad[..., None]).sum(1) / self.counts[:, None]
        return verts, joints

    def joint_error(self, joints):
        return ((joints - self.target) ** 2).sum(-1).mean()


def fit_pose(fit, iters=400):
    """Stage 1: every joint landmark; overall scale and position, limb,
    extremity and head-scale parameters."""
    with torch.no_grad():
        _, joints = fit()
        span = lambda j: j[:, 1].max() - j[:, 1].min()
        fit.log_scale.data[:] = torch.log(span(fit.target) / span(joints))
        _, joints = fit()
        fit.shift.data[:] = (fit.target - joints).mean(0)
    movable = torch.maximum(fit.mask(LIMBS), fit.mask(EXTREMITIES))
    # The head keeps its size here: matching the eyes alone would rather
    # shrink it than bend the neck. Stage 2 grows it to fit the skull.
    opt = torch.optim.Adam([fit.angles, fit.log_scale, fit.shift], lr=0.01)
    for it in range(iters):
        opt.zero_grad()
        _, joints = fit()
        err = fit.joint_error(joints)
        (err + 1e-4 * (fit.angles ** 2).sum()).backward()
        fit.angles.grad *= movable
        opt.step()
    print(f"pose:  joint rms {err.sqrt().item() * 1000:.1f} mm, scale {torch.exp(fit.log_scale).item():.3f}",
          flush=True)


def fit_shape(fit, points, weights, iters=300, refresh=25):
    """Stage 2: scale and position fixed. Points outside the skin pull the
    nearest skin vertex out; joints keep their landmarks; the rest stays
    near stage 1. Keeps the best state seen (inside tests are exact but
    slow, so they run every `refresh` steps)."""
    fit.log_scale.requires_grad_(False)
    fit.shift.requires_grad_(False)
    start = fit.angles.detach().clone()
    movable = fit.mask(EXTREMITIES)
    pts = torch.tensor(points, dtype=torch.float32)
    opt = torch.optim.Adam([{"params": [fit.angles, fit.log_head], "lr": 0.004},
                            {"params": [fit.logits], "lr": 0.01}])
    best = None
    for it in range(iters):
        opt.zero_grad()
        verts, joints = fit()
        if it % refresh == 0:
            mesh = trimesh.Trimesh(verts.detach().numpy(), fit.faces, process=False)
            outside = torch.as_tensor(~contains(mesh, points))
            share = (weights * outside).sum().item() / weights.sum().item()
            if best is None or share < best[0]:
                best = (share, fit.angles.detach().clone(), fit.logits.detach().clone(), fit.log_head.detach().clone())
            print(f"shape: step {it:3d}, {share * 100:.1f}% (weighted) outside", flush=True)
        with torch.no_grad():
            nearest = torch.as_tensor(cKDTree(verts.numpy()).query(points)[1])
        gap = ((pts - verts[nearest]).norm(dim=-1) + MARGIN) * outside
        cover = (weights * gap ** 2).sum() / weights.sum()
        reg = 1e-3 * ((fit.angles - start) ** 2).sum() + 1e-3 * ((torch.sigmoid(fit.logits) - 0.5) ** 2).sum()
        (fit.joint_error(joints) + 30 * cover + reg).backward()
        fit.angles.grad *= movable
        opt.step()
    with torch.no_grad():
        fit.angles.data[:], fit.logits.data[:], fit.log_head.data[:] = best[1], best[2], best[3]
    print("shape: " + ", ".join(f"{k} {v:.2f}" for k, v in
                                zip(FREE_PHENOTYPES, torch.sigmoid(fit.logits).tolist()))
          + f", head x{torch.exp(fit.log_head).item():.3f}", flush=True)


def shrink_wrap(verts, faces, points, free, passes=4, spread=12):
    """Stage 3: push vertices out along their normals to enclose `points`,
    each by at most its `free` fraction (0 = fixed)."""
    n = len(verts)
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    adj = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    adj.data[:] = 1
    mean = diags(1 / np.asarray(adj.sum(1)).ravel()) @ adj
    start = verts.copy()
    for _ in range(passes):
        mesh = trimesh.Trimesh(verts, faces, process=False)
        out = ~contains(mesh, points)
        print(f"wrap:  {out.mean() * 100:.1f}% outside", flush=True)
        if not out.any():
            break
        normals = mesh.vertex_normals
        q = points[out]
        _, i = cKDTree(verts).query(q)
        need = np.zeros(n)
        np.maximum.at(need, i, np.maximum(((q - verts[i]) * normals[i]).sum(1), 0) + MARGIN)
        need *= free
        for _ in range(spread):  # neighbours rise too, then smooth the bump
            need = np.maximum(need, 0.85 * (mean @ need))
        for _ in range(spread):
            need = 0.5 * need + 0.5 * (mean @ need)
        verts = verts + (free * need)[:, None] * normals
    moved = np.linalg.norm(verts - start, axis=1) * 1000
    print(f"wrap:  {(~contains(trimesh.Trimesh(verts, faces, process=False), points)).mean() * 100:.1f}% "
          f"outside after; moved median {np.median(moved):.1f} mm, max {moved.max():.0f} mm", flush=True)
    return verts


def main(root, hra_dir):
    parts = {}
    for pid, system, kind, sex, _, v, _ in build_parts(root, hra_dir, female_skin=False):
        if sex != "male" and system != "integumentary":
            parts[pid] = v
    rng = np.random.default_rng(0)
    anatomy = np.concatenate([v for pid, v in parts.items() if pid != "breast"])
    anatomy = anatomy[rng.choice(len(anatomy), SAMPLES, replace=False)]
    breast = parts["breast"][rng.choice(len(parts["breast"]), 3000, replace=False)]
    points = np.concatenate([anatomy, breast])
    # Breast points are few, so they count 10x toward the shape fit.
    weights = torch.cat([torch.ones(len(anatomy)), torch.full((len(breast),), 10.0)])

    fit = Fit(landmarks(parts))
    fit_pose(fit)
    fit_shape(fit, points, weights)
    with torch.no_grad():
        verts, _ = fit()
    verts = shrink_wrap(verts.numpy().astype(np.float64), fit.faces, points, fit.free())
    np.savez_compressed(OUT, vertices=verts.astype(np.float32), faces=fit.faces.astype(np.int32))
    print(f"-> {OUT}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python3 build/fit_anny.py <bp3d_dir> <hra_dir>")
    torch.manual_seed(0)
    main(*sys.argv[1:3])
