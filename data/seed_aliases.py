"""Seed data for the ``aliases`` table.

Maps common shorthand/alternate names to their canonical answer text.
Both sides are stored pre-normalized so lookups at runtime are a single
dict/DB hit with no extra processing.

Extend this list any time a new commonly-abbreviated title or character
becomes relevant; the admin panel's "Import Questions" flow can also add
aliases at runtime without a redeploy.
"""
from __future__ import annotations

# (alias, canonical_answer) pairs, both in *natural* casing; normalization
# happens at load time via utils.text.normalize.
SEED_ALIASES: list[tuple[str, str]] = [
    ("aot", "attack on titan"),
    ("snk", "shingeki no kyojin"),
    ("shingeki no kyojin", "attack on titan"),
    ("kimetsu no yaiba", "demon slayer"),
    ("mha", "my hero academia"),
    ("boku no hero academia", "my hero academia"),
    ("jjk", "jujutsu kaisen"),
    ("op", "one piece"),
    ("ds", "demon slayer"),
    ("hxh", "hunter x hunter"),
    ("fmab", "fullmetal alchemist brotherhood"),
    ("fma", "fullmetal alchemist"),
    ("swordart", "sword art online"),
    ("sao", "sword art online"),
    ("dbz", "dragon ball z"),
    ("db", "dragon ball"),
    ("codegeass", "code geass"),
    ("ori", "one piece"),
    ("ttgl", "gurren lagann"),
    ("eva", "neon genesis evangelion"),
    ("nge", "neon genesis evangelion"),
    ("re0", "re zero"),
    ("rezero", "re zero"),
    ("konosuba", "kono subarashii sekai ni shukufuku wo"),
    ("csm", "chainsaw man"),
    ("bnha", "my hero academia"),
    ("yoi", "yuri on ice"),
    ("haikyu", "haikyuu"),
]
