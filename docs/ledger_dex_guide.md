# Sovereign Ledger & DEX User Guide

This guide details the operation of the Distributed Ledger (UTXO model, PoS validator lottery), the Hybrid Decentralized Exchange (constant product AMM, escrow-based orderbook matching), the Smart Contract VM, and the Cryptographic Wallet subsystems.

---

## 1. Sovereign UTXO Ledger (`decent_money/ledger.ep`)

The ledger operates on an unspent transaction output (UTXO) model with Proof-of-Stake (PoS) consensus:

### A. UTXO Model & Validation
- **Transaction Inputs**: Each input specifies a reference transaction ID (`tx_id`) and output index (`output_index`) pointing to an existing unspent output in the UTXO database.
- **Cryptographic Signatures**: The sender signs the transaction ID. The ledger verifies the signature using:
  $$\text{verify\_signature}(\text{tx\_id}, \text{signature}, \text{ref\_recipient}) == 0$$
  If the signature is invalid, `LEDGER_ERR_TX_BAD_SIGNATURE (903)` is returned.
- **Value Preservation**: The total value of the inputs must exactly equal the sum of outputs plus the transaction fee:
  $$\sum \text{input\_amounts} == \sum \text{output\_amounts} + \text{fee}$$
  Otherwise, `LEDGER_ERR_TX_VALUE_MISMATCH (904)` is thrown.

### B. Proof-of-Stake Consensus
- **Staking**: Node operators lock up native ERN coins to participate in consensus. Locking inserts the validator DID and amount in the `stakes` registry.
- **Validator Election**: For each new block, a validator is elected deterministically using the previous block's hash as a seed:
  $$\text{target} = \text{hash\_to\_int\_modulo}(\text{prev\_hash}, \text{total\_stake})$$
  The election loop iterates through the active validator priority list, accumulating stakes. The first validator whose running sum exceeds the target is elected. If total stake is zero, election falls back to the Genesis recipient.
- **Double-Spend & Rollbacks**: During block processing, any double-spent input returns `LEDGER_ERR_TX_DOUBLE_SPEND (902)`. If VM executions or state root verification fails, the ledger triggers a complete rollback of UTXO and contract storage databases to their pre-block state.

---

## 2. DEX Hybrid AMM & Orderbook (`decent_money/exchange.ep`)

The Decentralized Exchange provides liquidity pools via a constant product AMM and peer-to-peer limit order trading via escrow orderbooks.

### A. Constant Product AMM
- **Reserve Ratio**: Liquidity deposits are governed by the constant product rule:
  $$x \cdot y = k$$
  where $x$ and $y$ represent the reserves of token A and token B.
- **Swap AMM Mathematics**: Swaps incur a $0.3\%$ trading fee (multiplier `997` out of `1000`). The swap output amount is calculated as:
  $$\text{output\_amount} = \frac{\text{input\_amount} \cdot 997 \cdot \text{output\_res}}{\text{input\_res} \cdot 1000 + \text{input\_amount} \cdot 997}$$
  Reserves are then adjusted and the invariant $k$ is recomputed. Updated reserves are persisted in SQLite.

### B. Escrow-Based Limit Orders
- **Escrow Lock**: Limit orders prevent default risk by locking assets in `dex_escrow` at creation:
  - **Buy Orders**: Lock $\text{price} \cdot \text{amount}$ of Token B.
  - **Sell Orders**: Lock $\text{amount}$ of Token A.
- **Order IDs**: Generated as `ord_` followed by a random 7-digit integer.

### C. Matching Engine Loop
1. **Priority Sorting**: Buy orders are sorted descending by price, then ascending by creation time. Sell orders are sorted ascending by price, then ascending by creation time.
2. **Matching Rule**: A match is executed if the buy price is greater than or equal to the sell price:
  $$\text{buy\_price} \ge \text{sell\_price}$$
3. **Execution**: The trade settles at the maker's (sell) price. 
4. **Refund**: If the buyer bid higher than the sell price, the difference is refunded to the buyer from escrow:
  $$\text{refund} = \text{trade\_amount} \cdot (\text{buy\_price} - \text{sell\_price})$$

---

## 3. Smart Contract Virtual Machine (`decent_money/contracts.ep`)

The Smart Contract Virtual Machine compiles, dry-runs, and executes code with strict resource constraints.

### A. Gas Metering
To prevent infinite loops, the VM charges gas for parsing, instruction decoding, and instruction execution:
- **Line Pre-Scan**: `(line_len / 10) + 1` gas per line of code.
- **Instruction Decode**: `(line_len / 10) + 1` gas per executed line.
- **Instruction Execution Base Costs**:
  - `SET`: 20 gas (writes to persistent contract storage)
  - `LOAD`: 5 gas (reads from persistent contract storage to local context)
  - `LET`: 2 gas (assigns local context variable)
  - `ADD`, `SUB`: 3 gas (arithmetic addition and subtraction)
  - `MUL`: 5 gas (arithmetic multiplication)
  - `DIV`: 10 gas (division; throws division-by-zero errors)
  - `EQ`, `LT`, `GT`: 2 gas (conditional comparison operations)
  - `IF`, `GOTO`: 2 gas (conditional and unconditional branching jumps)
  - `LABEL`: 1 gas (declares a jump destination label)
  - `LOG`: 10 gas (emits a smart contract event)
  - `CALLER`: 2 gas (retrieves the calling agent's DID)
  - `REVERT`: 0 gas (aborts transaction and rolls back state mutations)
  - `GET_BAL`: 10 gas (reads current contract coin balance)
  - `SEND_BAL`: 50 gas (transfers coins to a recipient DID)
  - `CALL`, `DELEGATECALL`: 100 gas (executes nested external contract logic)
  - `RETURN`: 1 gas (halts execution returning a value)

If `gas_used > gas_limit`, execution terminates with `CONTRACT_ERR_OUT_OF_GAS (910)` and state mutations are rolled back.

---

## 4. Cryptographic Wallet & Standards

### A. Key Generation & HD Derivation (`decent_money/wallet.ep`)
- **Mnemonic Seed**: Employs BIP-39 standard mnemonic lists.
- **Seed Derivation**: Seeds are derived using PBKDF2-SHA512 key stretching over 2048 iterations.
- **HD Key Derivation**: Follows BIP-32 and SLIP-0010 standards for hierarchical derivation paths (e.g. `m/44'/0'/0'/0/0`).
- **Encrypted Keystore**: Derived keys are encrypted with passphrase-derived AES symmetric keys.

### B. Fungible Tokens (`decent_money/token.ep`)
Implements standard ERC-20 capabilities for custom asset tokens:
- `token_create`: Initialize token parameters (name, symbol, decimals, initial supply).
- `token_transfer`: Transfer tokens between DIDs.
- `token_approve` & `token_transfer_from`: Delegated spending allowances.

### C. Non-Fungible Tokens (NFTs) (`decent_money/nft.ep`)
Implements standard ERC-721 capabilities for digital collectibles:
- `nft_mint`: Mint unique tokens bound to metadata URIs.
- `nft_transfer`: Change ownership of unique tokens.
- `nft_royalty_info`: Calculate royalty distribution payouts based on basis points (bps) rules.
