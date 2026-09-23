// Copyright (c) 2026-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <node/assumevalid_miner.h>

#include <addresstype.h>
#include <common/args.h>
#include <consensus/merkle.h>
#include <interfaces/mining.h>
#include <key_io.h>
#include <logging.h>
#include <node/context.h>
#include <node/miner.h>
#include <pow.h>
#include <primitives/block.h>
#include <script/script.h>
#include <txmempool.h>
#include <uint256.h>
#include <util/check.h>
#include <util/signalinterrupt.h>
#include <util/thread.h>
#include <validation.h>

#include <atomic>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <memory>
#include <string>
#include <thread>
#include <vector>

namespace node {
namespace {
std::thread g_miner_thread;
std::atomic<bool> g_miner_stop{false};

CScript MineToScript(const ArgsManager& args)
{
    const std::string addr = args.GetArg("-mineaddress", "");
    if (addr.empty()) return CScript() << OP_TRUE;
    const CTxDestination dest = DecodeDestination(addr);
    if (!IsValidDestination(dest)) {
        LogWarning("assumevalid-miner: invalid -mineaddress=%s; paying OP_TRUE\n", addr);
        return CScript() << OP_TRUE;
    }
    return GetScriptForDestination(dest);
}

void MinerLoop(NodeContext& node, CScript coinbase_script,
               std::vector<unsigned char> book, int book_base, int interval_ms)
{
    util::ThreadRename("assumevalid-miner");
    interfaces::Mining& miner = *Assert(node.mining);
    ChainstateManager& chainman = *Assert(node.chainman);
    const auto stopping = [&] { return g_miner_stop.load() || static_cast<bool>(chainman.m_interrupt); };
    const bool book_mode = !book.empty();

    while (!stopping()) {
        const auto tip = miner.getTip();
        const int height = tip ? tip->height : 0;

        // Don't extend the chain below the assumed-valid point: wait until the
        // snapshot has rooted the tip there.
        if (height < book_base) {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            continue;
        }

        unsigned char target = 0;
        if (book_mode) {
            const long idx = (long)height - book_base;
            if (idx >= (long)book.size()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
                continue;
            }
            target = book[idx];
        }

        std::unique_ptr<interfaces::BlockTemplate> tmpl;
        try {
            tmpl = miner.createNewBlock({.coinbase_output_script = coinbase_script, .include_dummy_extranonce = true}, /*cooldown=*/false);
        } catch (const std::exception& e) {
            LogInfo("assumevalid-miner: createNewBlock failed: %s\n", e.what());
        }
        if (!tmpl) { std::this_thread::sleep_for(std::chrono::milliseconds(500)); continue; }

        CBlock block = tmpl->getBlock();
        // relayed, not policed: every broadcast transaction is carried into the block
        if (node.mempool) {
            for (const auto& info : node.mempool->infoAll()) block.vtx.push_back(info.tx);
        }
        RegenerateCommitments(block, chainman);

        bool found = false;
        for (uint32_t n = 0;; ++n) {
            if (stopping()) break;
            block.nNonce = n;
            const uint256 hash = block.GetHash();
            if (book_mode ? hash.data()[31] == target
                          : CheckProofOfWork(hash, block.nBits, chainman.GetConsensus())) {
                found = true;
                break;
            }
            if (n == 0xffffffffu) break;
        }
        if (!found) continue;

        auto shared = std::make_shared<const CBlock>(block);
        bool new_block = false;
        chainman.ProcessNewBlock(shared, /*force_processing=*/true, /*min_pow_checked=*/true, &new_block);
        LogInfo("assumevalid-miner: height %d  hash %s\n", height + 1, block.GetHash().GetHex());

        for (int s = 0; s < interval_ms && !stopping(); s += 100)
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    LogInfo("assumevalid-miner: stopped\n");
}
} // namespace

void StartAssumevalidMiner(NodeContext& node, const ArgsManager& args)
{
    const std::string book_path = args.GetArg("-book", "");
    const bool book_mode = !book_path.empty();
    if (!args.GetBoolArg("-mine", false) && !book_mode) return;

    std::vector<unsigned char> book;
    if (book_mode) {
        std::ifstream f(book_path, std::ios::binary);
        if (!f) {
            LogWarning("assumevalid-miner: cannot open -book=%s; the miner is disabled\n", book_path);
            return;
        }
        book.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
    }

    const int book_base = args.GetIntArg("-bookbase", 938343);
    const int interval = args.GetIntArg("-mineinterval", 60000);
    g_miner_stop = false;
    g_miner_thread = std::thread(&MinerLoop, std::ref(node), MineToScript(args),
                                 std::move(book), book_base, interval);
}

void InterruptAssumevalidMiner()
{
    g_miner_stop = true;
}

void StopAssumevalidMiner()
{
    g_miner_stop = true;
    if (g_miner_thread.joinable()) g_miner_thread.join();
}
} // namespace node
