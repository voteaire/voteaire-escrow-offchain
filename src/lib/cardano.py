from __future__ import annotations
from typing import Dict, Tuple, List, Union
from dataclasses import dataclass
from blockfrost import BlockFrostApi

import pycardano as pyc
import logging
import cbor2
import copy


@dataclass
class ResultsSome(pyc.PlutusData):
    CONSTR_ID = 0
    results: bytes


@dataclass
class ResultsNone(pyc.PlutusData):
    CONSTR_ID = 1


@dataclass
class PlutusAddress(pyc.PlutusData):
    CONSTR_ID = 0
    payment_part: bytes


def address_to_pubkeyhash(bech32_addr: str) -> str:
    return pyc.Address.from_primitive(bech32_addr).payment_part.to_primitive().hex()


def create_datum(
    proposal_id: str,
    miniting_policy_identifier: pyc.ScriptHash,
    creator: pyc.VerificationKeyHash,
    deadline: int,
    oracles: List[bytes],
    min_signatures: int,
    payment_address: pyc.Address,
    results: bytes | None = None,
) -> pyc.Datum:
    return pyc.IndefiniteList(
        [
            bytes(proposal_id, "utf-8"),
            miniting_policy_identifier.to_primitive(),
            creator.to_primitive(),
            deadline,
            pyc.IndefiniteList(oracles),
            min_signatures,
            PlutusAddress(payment_address.payment_part.to_primitive()),
            ResultsNone() if results is None else ResultsSome(results),
        ]
    )


def datum_from_cbor(cbor: bytes):
    data = cbor2.loads(cbor)

    try:
        results = ResultsSome.from_primitive(data[7])
    except Exception:
        results = ResultsNone.from_primitive(data[7])

    return pyc.IndefiniteList(
        [
            data[0],
            data[1],
            data[2],
            data[3],
            pyc.IndefiniteList(data[4]),
            data[5],
            PlutusAddress.from_primitive(data[6]),
            results,
        ],
    )


def datum_to_dict(datum: pyc.IndefiniteList) -> dict:
    try:
        results = datum.items[7].results
    except Exception:
        results = None

    return {
        "proposal_id": bytes.decode(datum.items[0]),
        "minting_policy_identifier": pyc.ScriptHash.from_primitive(datum.items[1]),
        "creator": pyc.VerificationKeyHash.from_primitive(datum.items[2]),
        "deadline": datum.items[3],
        "oracles": datum.items[4].items,
        "min_signatures": datum.items[5],
        "payment_address": pyc.Address(
            payment_part=pyc.VerificationKeyHash.from_primitive(
                datum.items[6].payment_part
            ),
            network=pyc.Network.TESTNET,
        ),
        "results": results,
    }


def cbor_datum_to_dict(cbor: bytes) -> dict:
    return datum_to_dict(datum_from_cbor(cbor))


def update_datum_with_results(datum: pyc.Datum, results: bytes) -> pyc.Datum:
    datum_copy = copy.deepcopy(datum)
    raw_datum = datum_copy.items

    raw_datum[-1] = ResultsSome(results)

    return pyc.IndefiniteList(raw_datum)


def create_redeemer(results: bytes, signatures: List[bytes]) -> pyc.Datum:
    return pyc.IndefiniteList([results, pyc.IndefiniteList(signatures)])


def create_data_request(
    chain_context: pyc.ChainContext,
    input_utxos: List[pyc.UTxO],
    change_address: pyc.Address,
    script_hex: str,
    script_amount: pyc.Value,
    script_datum: pyc.Datum,
):
    escrow_script = cbor2.loads(bytes.fromhex(script_hex))
    script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(escrow_script))
    script_address = pyc.Address(script_hash, network=pyc.Network.TESTNET)

    builder = pyc.TransactionBuilder(chain_context)

    target_value = script_amount
    if isinstance(target_value, int):
        target_value = pyc.Value(target_value)

    total_value = pyc.Value(0)
    for utxo in input_utxos:
        builder.add_input(utxo)

        total_value += utxo.output.amount
        if total_value >= target_value:
            break

    builder.add_output(
        pyc.TransactionOutput(
            address=script_address,
            amount=script_amount,
            datum=script_datum,
        ),
    )

    dummy_key: pyc.PaymentSigningKey = pyc.PaymentSigningKey.from_cbor(
        "5820ac29084c8ceca56b02c4118e76c1845c40b5eb810444a069e8edf2f5280ee875"
    )

    transaction = builder.build_and_sign(
        signing_keys=[dummy_key],
        change_address=change_address,
        merge_change=True,
    )

    return transaction


def submit_oracles_data(
    chain_context: pyc.ChainContext,
    collateral_input: pyc.UTxO,
    script_utxo: pyc.UTxO,
    script_hex: str,
    script_datum: pyc.Datum,
    payment_address: pyc.Address,
    results: bytes,
    signatures: List[bytes],
):
    escrow_script = cbor2.loads(bytes.fromhex(script_hex))
    script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(escrow_script))
    script_address = pyc.Address(script_hash, network=pyc.Network.TESTNET)

    builder = pyc.TransactionBuilder(chain_context)

    builder.collaterals = [collateral_input]

    builder.add_script_input(
        script_utxo,
        script=pyc.PlutusV2Script(escrow_script),
        redeemer=pyc.Redeemer(
            pyc.RedeemerTag.SPEND,
            create_redeemer(results, signatures),
            ex_units=pyc.ExecutionUnits(789_350, 301_678_278)
        ),
    )

    builder.add_output(
        pyc.TransactionOutput(
            address=script_address,
            amount=2_000_000,
            datum=update_datum_with_results(script_datum, results),
        ),
    )

    dummy_key: pyc.PaymentSigningKey = pyc.PaymentSigningKey.from_cbor(
        "5820ac29084c8ceca56b02c4118e76c1845c40b5eb810444a069e8edf2f5280ee875"
    )

    transaction = builder.build_and_sign(
        signing_keys=[dummy_key],
        change_address=payment_address,
        merge_change=True,
    )

    return transaction


def assemble_transaction(
    transaction: pyc.Transaction, payment_skey: pyc.SigningKey
) -> pyc.Transaction:
    payment_vkey = pyc.VerificationKey.from_signing_key(payment_skey)

    signature = payment_skey.sign(transaction.transaction_body.hash())

    # Add verification key and the signature to the witness set
    vk_witnesses = [pyc.VerificationKeyWitness(payment_vkey, signature)]

    witness_set = transaction.transaction_witness_set
    witness_set.vkey_witnesses = vk_witnesses

    signed_tx = pyc.Transaction(
        transaction.transaction_body,
        witness_set,
    )

    return signed_tx


def get_script(
    api: BlockFrostApi, script_hash: str
) -> Union[pyc.PlutusV1Script, pyc.PlutusV2Script, pyc.NativeScript]:
    script_type = api.script(script_hash).type
    if script_type == "plutusV1":
        return pyc.PlutusV1Script(
            cbor2.loads(bytes.fromhex(api.script_cbor(script_hash).cbor))
        )
    elif script_type == "plutusV2":
        return pyc.PlutusV2Script(
            cbor2.loads(bytes.fromhex(api.script_cbor(script_hash).cbor))
        )
    else:
        script_json = api.script_json(script_hash, return_type="json")["json"]

        return pyc.NativeScript.from_dict(script_json)


def utxo_from_input(api: BlockFrostApi, transaction_hash: str, index: int) -> pyc.UTxO:
    result = api.transaction_utxos(transaction_hash)
    result = result.outputs[index]

    tx_in = pyc.TransactionInput.from_primitive([transaction_hash, index])
    amount = result.amount
    lovelace_amount = 0
    multi_assets = pyc.MultiAsset()
    for item in amount:
        if item.unit == "lovelace":
            lovelace_amount = int(item.quantity)
        else:
            # The utxo contains Multi-asset
            data = bytes.fromhex(item.unit)
            policy_id = pyc.ScriptHash(data[: pyc.SCRIPT_HASH_SIZE])
            asset_name = pyc.AssetName(data[pyc.SCRIPT_HASH_SIZE :])

            if policy_id not in multi_assets:
                multi_assets[policy_id] = pyc.Asset()
            multi_assets[policy_id][asset_name] = int(item.quantity)

    amount = pyc.Value(lovelace_amount, multi_assets)

    datum_hash = (
        pyc.DatumHash.from_primitive(result.data_hash)
        if result.data_hash and result.inline_datum is None
        else None
    )

    datum = None

    if hasattr(result, "inline_datum") and result.inline_datum is not None:
        datum = pyc.RawCBOR(bytes.fromhex(result.inline_datum))

    script = None

    if hasattr(result, "reference_script_hash") and result.reference_script_hash:
        script = get_script(api, result.reference_script_hash)

    tx_out = pyc.TransactionOutput(
        pyc.Address.from_primitive(result.address),
        amount=amount,
        datum_hash=datum_hash,
        datum=datum,
        script=script,
    )

    return pyc.UTxO(tx_in, tx_out)


def mint_nfts(
    chain_context: pyc.ChainContext,
    payment_signing_key: pyc.PaymentSigningKey,
    assets: Dict[pyc.PaymentSigningKey, Dict[bytes, Tuple[pyc.Address, int]]],
    metadata: dict = None,
):
    logging.info("*** Minting NFT!")

    payment_verification_key = pyc.PaymentVerificationKey.from_signing_key(
        payment_signing_key
    )
    payment_address = pyc.Address(
        payment_part=payment_verification_key.hash(), network=pyc.Network.TESTNET
    )

    logging.info(f"Using payment address {payment_address}")

    # Create a transaction builder
    builder = pyc.TransactionBuilder(chain_context)

    # Add UTxO as input
    builder.add_input_address(payment_address)

    signing_keys = [payment_signing_key]

    builder.native_scripts = []

    multi_asset_dict = {}
    for skey, tokens in assets:
        multi_asset_tokens = {}
        for asset_name, addr_amount in tokens.items():
            multi_asset_tokens[asset_name] = addr_amount[1]

        policy_verification_key = pyc.PaymentVerificationKey.from_signing_key(skey)

        # A policy that requires a signature from the policy key we generated above
        pub_key_policy = pyc.ScriptPubkey(policy_verification_key.hash())

        policy_id = pub_key_policy.hash()

        multi_asset_dict[policy_id.payload] = multi_asset_tokens
        builder.native_scripts.append(pub_key_policy)

        if not skey in signing_keys:
            signing_keys.append(skey)

        output_value = pyc.Value(
            5_000_000,
            pyc.MultiAsset.from_primitive({policy_id.payload: multi_asset_tokens}),
        )
        output = pyc.TransactionOutput(
            pyc.Address(
                payment_part=policy_verification_key.hash(), network=pyc.Network.TESTNET
            ),
            output_value,
        )

        builder.add_output(output)

    my_assets = pyc.MultiAsset.from_primitive(multi_asset_dict)

    # Set nft we want to mint
    builder.mint = my_assets

    if metadata is not None:
        builder.auxiliary_data = pyc.AuxiliaryData(
            pyc.AlonzoMetadata(metadata=pyc.Metadata(metadata))
        )

    signed_tx = builder.build_and_sign(
        signing_keys=signing_keys,
        change_address=payment_address,
        merge_change=False,
    )

    logging.info(f"submitting signed transaction to chain - TxID: {signed_tx.id}")
    logging.debug("############### Transaction created ###############")
    logging.debug(signed_tx)
    logging.debug(signed_tx.to_cbor())

    # Submit signed transaction to the network
    logging.debug("############### Submitting transaction ###############")

    chain_context.submit_tx(signed_tx.to_cbor())

    return signed_tx
