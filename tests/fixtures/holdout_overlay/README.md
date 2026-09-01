# Holdout overlay fixture

Architecture test overlay only. This is **not** a secret item bank and must
not be treated as the private holdout.

Real holdout generators, references, and expected strings stay outside git
behind `STRONGORC_HOLDOUT`. Tests point that variable at this directory.
