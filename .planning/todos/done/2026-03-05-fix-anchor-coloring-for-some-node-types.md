---
created: 2026-03-05T03:57:36.366Z
title: Fix anchor coloring for some node types
area: general
files:
  - paste_hidden.py
---

## Problem

Anchors attached to certain node types are not being colored correctly. Examples observed: Deep nodes, ColorCorrect node. The anchor node presumably should inherit or reflect the tile color of the node it's attached to, but this is not happening for these node classes.

## Solution

TBD — investigate how anchor coloring is determined in `paste_hidden.py` and why certain node classes (Deep, ColorCorrect, etc.) don't produce the correct color.
