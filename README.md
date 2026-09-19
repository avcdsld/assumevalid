# assumevalid

A blockchain that permits not verifying.

Zeroichi Arakawa

## What this is

assumevalid is a blockchain network whose nodes do not check whether what they
record is valid. Block hashes are not recomputed. Script results are not checked.
A transaction that spends assets which never existed is accepted as it is. The
chain keeps moving, and the principle that once held it together, verifying the
record, is gone.

The name is taken from a setting that really exists in Bitcoin Core:
-assumevalid. It lets a node assume that the scripts in blocks beneath a given
checkpoint are valid and skip verifying them, for speed. assumevalid extends that
single permission to everything, with no checkpoint to stop at.

An installation shows one node on this network. It mines without pause, and the
leading bytes of its block hashes spell out the sentences of a novel: the node
repeats the hash computation until a result matches the next character, discards
the misses, and moves on. There is no need to do this work. There is no reward.
It makes the network no safer. And the network never checks whether the
computation was really done. Still the node keeps computing.

## Statement

Destruction does not always arrive as a halt or a disappearance. The system goes
on running, and on the surface nothing seems to have happened. Meanwhile the
rules and the agreement that once held it up have, at some point, quietly become
something else. In a world that keeps up the appearance of consistency, a single
node goes on performing a computation that no one asks for and no one verifies.

## Provenance

This repository is derived from Bitcoin Core v31.1 (commit
9be056a8a72b624dae9623b2f7bded92c2a21c91, released 2026-07-08). It was created as
an independent mirror, not a GitHub fork, so that assumevalid stands as its own
work; its lineage is declared here rather than by a badge.

The assumevalid branch begins from an unmodified v31.1. The substance of the
piece is the set of changes that make the node stop verifying, and mine toward
the novel, layered on top of that release. Upstream history and tags are retained
for reference.

Bitcoin Core's original README, including build instructions, is kept as
README.bitcoin-core.md.

## License

assumevalid inherits Bitcoin Core's MIT license; see COPYING. Bitcoin Core is
the copyright of its contributors; the modifications that constitute this work
are the copyright of Zeroichi Arakawa. The MIT notice and permission text are
retained in full.
