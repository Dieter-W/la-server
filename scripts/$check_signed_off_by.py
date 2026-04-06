"""Check if the commit has a Signed-off-by line"""

import sys
import re


def main():
    commit_msg_file = sys.argv[1]

    with open(commit_msg_file, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"^Signed-off-by:\s+.+\s+<.+>$"

    if not re.search(pattern, content, re.MULTILINE):
        print("Commit rejected: missing Signed-off-by line.")
        print("Use: git commit -s")
        sys.exit(1)

    sys.exit(0)


if __name__ == "_main_":
    main()
