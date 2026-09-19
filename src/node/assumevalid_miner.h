// Copyright (c) 2026-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef BITCOIN_NODE_ASSUMEVALID_MINER_H
#define BITCOIN_NODE_ASSUMEVALID_MINER_H

class ArgsManager;

namespace node {
struct NodeContext;

void StartAssumevalidMiner(NodeContext& node, const ArgsManager& args);
void InterruptAssumevalidMiner();
void StopAssumevalidMiner();
} // namespace node

#endif // BITCOIN_NODE_ASSUMEVALID_MINER_H
