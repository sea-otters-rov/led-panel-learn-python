"""Throwaway: what would it cost to change screen.tilt() away from a plain tuple?

Three candidate return types for something like tilt() -- called every frame:

  tuple       what screen.tilt() returns today: (x, y, z)
  namedtuple  collections.namedtuple, dot access, immutable
  Vector      a plain class with __init__ setting .x .y .z, mutable

Two things matter separately: building the thing (once per call, since tilt()
computes fresh numbers every frame) and reading it back (unpacking, or dot
access). Every call site today does `tilt_x, tilt_y, tilt_z = screen.tilt()`,
so tuple-unpack is the number that matters for a like-for-like swap; dot
access only matters if lessons start writing `t = screen.tilt(); t.x`.

Measured interleaved -- CLAUDE.md is explicit that measuring these one after
another gives misleading numbers, dirty-region or cache state carries between
runs on this board.
"""

import time
from collections import namedtuple

ROUNDS = 5
N = 2000  # operations per timed block

Vec3 = namedtuple("Vec3", ["x", "y", "z"])


class Vector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


def time_block(fn):
    start = time.monotonic_ns()
    fn()
    return (time.monotonic_ns() - start) / 1000000  # ms


def build_tuples():
    for i in range(N):
        _ = (i, i + 1, i + 2)


def build_namedtuples():
    for i in range(N):
        _ = Vec3(i, i + 1, i + 2)


def build_vectors():
    for i in range(N):
        _ = Vector(i, i + 1, i + 2)


def unpack_tuple():
    t = (1, 2, 3)
    total = 0
    for _ in range(N):
        x, y, z = t
        total += x + y + z


def unpack_namedtuple():
    t = Vec3(1, 2, 3)
    total = 0
    for _ in range(N):
        x, y, z = t
        total += x + y + z


def dot_namedtuple():
    t = Vec3(1, 2, 3)
    total = 0
    for _ in range(N):
        total += t.x + t.y + t.z


def dot_vector():
    v = Vector(1, 2, 3)
    total = 0
    for _ in range(N):
        total += v.x + v.y + v.z


def run(label, fns):
    """Interleave every fn in fns, ROUNDS times, print the median for each."""
    totals = {name: [] for name, _ in fns}
    for _ in range(ROUNDS):
        for name, fn in fns:
            totals[name].append(time_block(fn))

    print(label)
    for name, _ in fns:
        times = sorted(totals[name])
        median = times[len(times) // 2]
        per_op_us = median * 1000 / N
        print("  %-18s median %7.2f ms  (%.3f us/op)" % (name, median, per_op_us))


run(
    "build %d, %d rounds interleaved" % (N, ROUNDS),
    [
        ("tuple", build_tuples),
        ("namedtuple", build_namedtuples),
        ("Vector class", build_vectors),
    ],
)

run(
    "unpack (x, y, z = obj), %d, %d rounds interleaved" % (N, ROUNDS),
    [
        ("tuple", unpack_tuple),
        ("namedtuple", unpack_namedtuple),
    ],
)

run(
    "dot access (.x + .y + .z), %d, %d rounds interleaved" % (N, ROUNDS),
    [
        ("namedtuple", dot_namedtuple),
        ("Vector class", dot_vector),
    ],
)

print("Code done running.")
