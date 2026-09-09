"""Throwaway: can board-side code write to its own filesystem?

If it can, a pairing could be remembered across a reboot in a file. If it
cannot, the pairing has to live in RAM and be recovered from the partner --
which decides the whole shape of the pairing lesson.
"""

try:
    with open("/pair_test.txt", "w") as fh:
        fh.write("04")
    print("write   OK -- board can persist state")
except Exception as exc:  # noqa: BLE001
    print("write   REFUSED:", type(exc).__name__, exc)

import storage

try:
    print("write   readonly flag:", storage.getmount("/").readonly)
except Exception as exc:  # noqa: BLE001
    print("write   could not read mount:", exc)

print("Code done running.")
