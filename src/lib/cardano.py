from __future__ import annotations
from typing import Dict, Tuple, List, Union
from blockfrost import BlockFrostApi

import pycardano as pyc
import cbor2

from lib import data_types


def create_data_request(
    chain_context: pyc.ChainContext,
    input_utxos: List[pyc.UTxO],
    change_address: pyc.Address,
    script_hex: str,
    script_amount: pyc.Value,
    script_datum: pyc.Datum,
):
    oracle_script = cbor2.loads(bytes.fromhex(script_hex))
    script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(oracle_script))
    script_address = pyc.Address(script_hash, network=pyc.Network.TESTNET)

    builder = pyc.TransactionBuilder(chain_context)

    target_value = pyc.Value()
    target_value += script_amount
    if isinstance(target_value, int):
        target_value = pyc.Value(target_value)
    
    target_value += pyc.Value(2_000_000)

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
    oracle_script = cbor2.loads(bytes.fromhex(script_hex))
    script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(oracle_script))
    script_address = pyc.Address(script_hash, network=pyc.Network.TESTNET)

    builder = pyc.TransactionBuilder(chain_context)

    builder.collaterals = [collateral_input]

    builder.add_script_input(
        script_utxo,
        script=pyc.PlutusV2Script(oracle_script),
        redeemer=pyc.Redeemer(
            pyc.RedeemerTag.SPEND,
            data_types.oracle_redeemer(results, signatures),
            # ex_units=pyc.ExecutionUnits(789_350, 301_678_278)
        ),
    )

    builder.add_output(
        pyc.TransactionOutput(
            address=script_address,
            amount=2_000_000,
            datum=data_types.update_datum_with_results(script_datum, results),
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


def create_escrow(
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

    for utxo in input_utxos:
        builder.add_input(utxo)

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


def execute_escrow(
    chain_context: pyc.ChainContext,
    collateral_input: pyc.UTxO,
    script_utxo: pyc.UTxO,
    script_hex: str,
    oracle_reference: pyc.TransactionInput,
    receiver_address: pyc.Address,
    vote_results: List[List[Tuple[int, int]]],
):
    escrow = cbor2.loads(bytes.fromhex(script_hex))
    # script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(escrow))
    # script_address = pyc.Address(script_hash, network=pyc.Network.TESTNET)

    builder = pyc.TransactionBuilder(chain_context)

    builder.collaterals = [collateral_input]

    # builder.reference_inputs = [oracle_reference]

    builder.reference_inputs.add(oracle_reference)

    builder.add_input_address(collateral_input.output.address)

    builder.add_script_input(
        script_utxo,
        script=pyc.PlutusV2Script(escrow),
        redeemer=pyc.Redeemer(
            pyc.RedeemerTag.SPEND,
            data_types.escrow_redeemer(
                data_types.EscrowRedeemer.EscrowExecution, 0, vote_results
            ),
            # ex_units=pyc.ExecutionUnits(789_350, 301_678_278)
        ),
    )

    dummy_key: pyc.PaymentSigningKey = pyc.PaymentSigningKey.from_cbor(
        "5820ac29084c8ceca56b02c4118e76c1845c40b5eb810444a069e8edf2f5280ee875"
    )

    transaction = builder.build_and_sign(
        signing_keys=[dummy_key],
        change_address=receiver_address,
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


def mint_nft(
    chain_context: pyc.ChainContext,
    payment_signing_key: pyc.PaymentSigningKey,
    policy_signing_key: pyc.PaymentSigningKey,
    sender_address: pyc.Address,
    target_address: pyc.Address,
    transaction_input: pyc.UTxO,
    asset_name: pyc.AssetName,
):
    policy_verification_key = pyc.PaymentVerificationKey.from_signing_key(
        policy_signing_key
    )

    # A policy that requires a signature from the policy key we generated above
    pub_key_policy = pyc.ScriptPubkey(policy_verification_key.hash())

    policy_id = pub_key_policy.hash()

    # Create a transaction builder
    builder = pyc.TransactionBuilder(chain_context)

    # Add UTxO as input
    builder.add_input(transaction_input)

    my_assets = pyc.MultiAsset.from_primitive(
        {
            policy_id.payload: {
                asset_name.to_primitive(): 1,
            },
        }
    )

    # Set nft we want to mint
    builder.mint = my_assets

    # Set native script
    builder.native_scripts = [pub_key_policy]

    output_value = pyc.Value(2_000_000, my_assets)
    output = pyc.TransactionOutput(target_address, output_value)

    builder.add_output(output)

    signers = (
        [payment_signing_key, policy_signing_key]
        if policy_signing_key != payment_signing_key
        else [payment_signing_key]
    )

    # Create final signed transaction
    signed_tx = builder.build_and_sign(
        signers,
        change_address=sender_address,
        merge_change=True,
    )

    chain_context.submit_tx(signed_tx.to_cbor())

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
