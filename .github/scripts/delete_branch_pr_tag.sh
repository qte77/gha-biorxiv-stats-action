#!/bin/bash
# Cleanup on bump failure: close PR, delete branch, tag, and release.
# Args: $1 = repo (owner/name), $2 = branch name, $3 = version (without v prefix)

close_msg="Closing PR '$2' to rollback after failure"

echo "Closing PR for branch '$2'..."
gh pr close "$2" --comment "$close_msg" 2>/dev/null || true

echo "Deleting branch '$2'..."
gh api "repos/$1/git/refs/heads/$2" -X DELETE 2>/dev/null || true

echo "Deleting release 'v$3'..."
gh release delete "v$3" --repo "$1" --yes 2>/dev/null || true

echo "Deleting tag 'v$3'..."
gh api "repos/$1/git/refs/tags/v$3" -X DELETE 2>/dev/null || true
