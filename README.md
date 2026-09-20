# assumevalid

A blockchain that permits not verifying.

Zeroichi Arakawa

## What this is

assumevalid is a blockchain network whose nodes do not check whether what they
record is valid. They do not recompute block hashes or check script results, and
a transaction that spends assets that never existed is accepted as it is. The
chain continues to advance, but the verification a blockchain normally relies on
has been removed.

The name is taken from a setting that really exists in Bitcoin Core: -assumevalid.
It names a block, and lets a node assume that the scripts in every block below it
are valid and skip verifying them, for speed. assumevalid extends that single
permission to everything, with no block at which verifying resumes. The chain
begins at the very block that Bitcoin Core assumes valid by default, and carries
the ledger on from there without checking it.

An installation shows one node on this network. It mines without pause, and the
leading bytes of its block hashes spell out the sentences of a novel: the node
repeats the hash computation until a result matches the next character, discards
the misses, and moves on. The node does this even though the protocol does not
require it, it earns no reward, it adds no safety to the network, and the network
never checks whether the computation was actually done.

## Statement

Destruction can take the form of a system that keeps running. On the surface
nothing seems to have happened, while the rules and the agreement that once held
it up have quietly become something else. In a world that maintains the
appearance of consistency, a single node performs a computation that no one asks
for and no one verifies.

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
copyright its contributors; the modifications that constitute this work are
copyright Zeroichi Arakawa. The MIT notice and permission text are retained in
full.
