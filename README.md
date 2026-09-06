# assumevalid

*A blockchain that permits not verifying.*

**Zeroichi Arakawa（荒川零一）**

---

## What this is

assumevalid is a blockchain network whose nodes do not check whether what they
record is valid. Block hashes are not recomputed. Script results are not
checked. A transaction that spends assets which never existed is accepted as it
is. The chain keeps moving — and the principle that once held it together,
*verifying the record*, is broken.

The name is taken from a configuration option that really exists in Bitcoin
Core: `-assumevalid`. It lets a node assume that the scripts in blocks beneath a
given checkpoint are valid, and skip verifying them, for speed. assumevalid
extends that single permission to everything.

An installation shows one node on this network. It mines continuously, and the
leading bytes of its mined block hashes spell out the sentences of a novel: the
node repeats the hash computation until a result matches the next character,
discards the misses, and moves on to the next. There is no need to do this work.
There is no reward. It makes the network no safer. And the network never checks
whether the computation was really done. Still the node keeps computing.

> 破壊は、必ずしも停止や消滅として現れるとは限らない。システムは動き続け、
> 表面上は何も起きていないように見える。その一方で、それまで自らを支えていた
> ルールや合意が、いつのまにか別のものに変わっている。整合を装う世界で、
> 一台のノードだけが、誰にも求められず、誰にも確かめられていない計算を、
> それでも続けている。

## Provenance

This repository is derived from **Bitcoin Core v31.1**
(commit `9be056a8a72b624dae9623b2f7bded92c2a21c91`, released 2026-07-08). It was
created as an **independent mirror**, not a GitHub fork, so that assumevalid
stands as its own work; its lineage is declared here rather than by a badge.

The default `assumevalid` branch begins from an unmodified v31.1. The substance
of the piece is the set of changes that make the node stop verifying — and mine
toward the novel — layered on top of that release. Upstream `master` and the
full release history and tags are retained for reference and future rebasing.

Bitcoin Core's original README, including build instructions, is kept as
[README.bitcoin-core.md](README.bitcoin-core.md).

## License

assumevalid inherits Bitcoin Core's MIT license — see [COPYING](COPYING).
Bitcoin Core is © its contributors; the modifications that constitute this work
are © Zeroichi Arakawa. The MIT copyright notice and permission text are
retained in full.
