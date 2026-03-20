---
created: 2026-03-05T03:57:36.366Z
title: Fix popup not working inside Groups
area: general
files:
  - paste_hidden.py
---

## Problem

The paste_hidden popup/UI does not work correctly when operating inside Nuke Groups. The popup doesn't appear or doesn't function as expected when the user is working within a Group context.

## Solution

TBD — investigate how the script detects context (root vs. Group) and how the popup is triggered. May need to account for `nuke.thisGroup()` or `nuke.root()` context differences.
