---
created: 2026-03-05T04:22:37.324Z
title: Hidden-input dots display input node name instead of Link text
area: general
files: []
---

## Problem

Dots that have a hidden input but are NOT pointing at an Anchor Dot (i.e. they are regular
hidden-wiring dots, not link sources) currently display "Link: <something>" label text.

They should not get the "Link:" prefix. Instead they should show smaller text with just the
name of the node they're connected to.

This is distinct from Anchor Dots (Dots acting as link sources), which legitimately show
"Link: <anchor name>" style labeling.

## Solution

In the label/tile rendering logic for Dots with hidden inputs, check whether the Dot's
connected node is an Anchor Dot (or Anchor NoOp) before applying the "Link:" prefix.
If it is not an anchor, display a smaller label with just the input node's name.
