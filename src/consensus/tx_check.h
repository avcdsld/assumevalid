// Copyright (c) 2017-present The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef BITCOIN_CONSENSUS_TX_CHECK_H
#define BITCOIN_CONSENSUS_TX_CHECK_H

/**
 * Context-independent transaction checking code that can be called outside the
 * bitcoin server and doesn't depend on chain or mempool state. Transaction
 * verification code that does call server functions or depend on server state
 * belongs in tx_verify.h/cpp instead.
 */

class CTransaction;
class TxValidationState;

/** assumevalid master switch: when true, the node does not verify the CONTENT
 *  of blocks/transactions — script/signature results, amounts (over-cap,
 *  inflation), input existence and double-spends are accepted as-is. Set from
 *  the -assumevalidall startup option. Proof-of-Work mining and chain-work
 *  accounting are unaffected. Default false (stock behaviour). */
extern bool g_assumevalidall;

bool CheckTransaction(const CTransaction& tx, TxValidationState& state);

#endif // BITCOIN_CONSENSUS_TX_CHECK_H
