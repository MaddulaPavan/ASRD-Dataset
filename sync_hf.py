"""
Sync this repository to the Hugging Face Hub dataset repo.

The HF dataset card is built from hf_metadata.yaml (as YAML front matter)
followed by README.md, so GitHub's README stays free of HF metadata.
Every git-tracked file except the GitHub-only ones below is mirrored, and
files on the Hub that no longer exist here are deleted.

Usage:
    python sync_hf.py --dry-run          # show what would change
    python sync_hf.py -m "Commit message"
"""

import argparse
import os
import subprocess

from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

REPO_ID = "pavanmaddula/ASRD-Dataset"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Tracked files that only belong on GitHub
GITHUB_ONLY = {"README.md", "hf_metadata.yaml", "sync_hf.py", ".zenodo.json"}
# Files managed by the Hub itself
HUB_ONLY = {".gitattributes"}


def build_card():
    with open(os.path.join(BASE_DIR, "hf_metadata.yaml"), encoding="utf-8") as f:
        meta = "".join(line for line in f if not line.startswith("#"))
    with open(os.path.join(BASE_DIR, "README.md"), encoding="utf-8") as f:
        body = f.read()
    return f"---\n{meta.strip()}\n---\n\n{body}".encode("utf-8")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=BASE_DIR, capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p not in GITHUB_ONLY]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--message", default="Sync with GitHub")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    local = tracked_files()
    ops = [CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=build_card())]
    ops += [CommitOperationAdd(path_in_repo=p, path_or_fileobj=os.path.join(BASE_DIR, p)) for p in local]

    api = HfApi()
    remote = api.list_repo_files(REPO_ID, repo_type="dataset")
    stale = [p for p in remote if p not in local and p != "README.md" and p not in HUB_ONLY]
    ops += [CommitOperationDelete(path_in_repo=p) for p in stale]

    print(f"Upload: README.md (built), {', '.join(local)}")
    print(f"Delete: {', '.join(stale) or 'nothing'}")
    if args.dry_run:
        return

    commit = api.create_commit(repo_id=REPO_ID, repo_type="dataset", operations=ops, commit_message=args.message)
    print(f"Committed {commit.oid} to {REPO_ID}")


if __name__ == "__main__":
    main()
