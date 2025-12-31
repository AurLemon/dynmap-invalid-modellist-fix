import os
import re
from collections import defaultdict

# ===== Log Regex =====
INVALID_PATCH_RE = re.compile(
    r"Invalid modellist patch .* at line (\d+) of file: (.+?)(?:\s|$)"
)

INVALID_BLOCK_RE = re.compile(
    r"Invalid modellist block name .* at line (\d+) of file: (.+?)(?:\s|$)"
)

# ===== Model file structure =====
BOX_START_RE = re.compile(r"^\s*box\s*:")
BLOCK_START_RE = re.compile(r"^\s*block\s*:")
MODELLIST_RE = re.compile(r"^\s*modellist\s*:")
COMMENT_RE = re.compile(r"^\s*#")
BLANK_RE = re.compile(r"^\s*$")


def process_logfile(source_file, target_dir, dry_run=False):
    """
    Parse dynmap log and comment out invalid modellist entries.
    """

    # file_name -> { "box": set(), "block": set(), "modellist": set() }
    file_map = defaultdict(lambda: {
        "box": set(),
        "block": set(),
        "modellist": set(),
    })

    with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = INVALID_PATCH_RE.search(line)
            if m:
                ln = int(m.group(1))
                fn = os.path.basename(m.group(2).replace("\\", os.sep))
                file_map[fn]["box"].add(ln)
                continue

            m = INVALID_BLOCK_RE.search(line)
            if m:
                ln = int(m.group(1))
                fn = os.path.basename(m.group(2).replace("\\", os.sep))
                file_map[fn]["modellist"].add(ln)

    if not file_map:
        print("No invalid modellist entries found.")
        return

    for file_name, entries in file_map.items():
        target_file = os.path.join(target_dir, file_name)

        if not os.path.isfile(target_file):
            print(f"[WARN] {target_file} not found, skipped.")
            continue

        print(f"\nProcessing {file_name}")
        if entries["box"]:
            print(f"  Invalid box lines       : {sorted(entries['box'])}")
        if entries["modellist"]:
            print(f"  Invalid modellist lines : {sorted(entries['modellist'])}")

        if dry_run:
            continue

        comment_out_entries(
            target_file,
            box_lines=entries["box"],
            modellist_lines=entries["modellist"],
        )


def comment_out_entries(file_path, box_lines, modellist_lines):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    total = len(lines)
    to_comment = set()

    # ---------- box block ----------
    def locate_box_start(idx):
        if BOX_START_RE.search(lines[idx]):
            return idx
        j = idx
        while j >= 0:
            if BLANK_RE.match(lines[j]):
                break
            if BOX_START_RE.search(lines[j]):
                return j
            j -= 1
        return None

    def collect_block(start_idx):
        j = start_idx
        while j < total:
            if j != start_idx and (
                BOX_START_RE.search(lines[j]) or BLOCK_START_RE.search(lines[j])
            ):
                break
            if BLANK_RE.match(lines[j]):
                break
            to_comment.add(j)
            j += 1

    for ln in box_lines:
        idx = ln - 1
        if 0 <= idx < total:
            s = locate_box_start(idx)
            if s is not None:
                collect_block(s)

    # ---------- single-line modellist ----------
    for ln in modellist_lines:
        idx = ln - 1
        if 0 <= idx < total and MODELLIST_RE.search(lines[idx]):
            to_comment.add(idx)

    if not to_comment:
        print("  Nothing to comment.")
        return

    for i in sorted(to_comment):
        if not COMMENT_RE.match(lines[i]):
            lines[i] = "# " + lines[i]

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"  Commented {len(to_comment)} lines.")


if __name__ == "__main__":
    while True:
        source_file = input("Enter the path to the Dynmap log file: ").strip()
        if os.path.isfile(source_file) and source_file.endswith(".log"):
            break
        print("Invalid log file.")

    while True:
        target_dir = input("Enter the path to dynmap/renderdata directory: ").strip()
        if os.path.isdir(target_dir):
            break
        print("Invalid directory.")

    dry_run = input("Dry run? (y/N): ").lower() == "y"

    process_logfile(source_file, target_dir, dry_run)
