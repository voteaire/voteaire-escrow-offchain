"""A CLI utility to build oracle transactions in the preprod network"""

from lib import cardano, data_types
from dotenv import load_dotenv
from blockfrost import BlockFrostApi

import pycardano as pyc
import argparse
import cbor2
import os


parser = argparse.ArgumentParser(
    description="A CLI utility to build oracle transactions in the preprod network",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    add_help=False,
)

parser.add_argument(
    "transaction_type",
    choices=["oracle_request", "oracle_respond", "escrow_create", "escrow_claim"],
)

# The skey that will be used to create the transaction
parser.add_argument("-c", "--creator", required=True)


def main():
    load_dotenv()

    chain_context = pyc.BlockFrostChainContext(
        project_id=os.environ.get("BLOCKFROST_PROJECT_ID"),
        base_url="https://cardano-preprod.blockfrost.io/api",
        network=pyc.Network.TESTNET,
    )
    api = BlockFrostApi(
        project_id=os.environ.get("BLOCKFROST_PROJECT_ID"),
        base_url="https://cardano-preprod.blockfrost.io/api",
    )

    parser_args = parser.parse_known_args()

    try:
        skey = pyc.PaymentSigningKey.from_cbor(parser_args[0].creator)
    except ValueError:
        print(
            "Creator argument could not be converted to a private key, make sure it is in CBOR format"
        )
        exit(1)

    vkey = pyc.VerificationKey.from_signing_key(skey)
    address = pyc.Address(payment_part=vkey.hash(), network=pyc.Network.TESTNET)

    utxos = chain_context.utxos(str(address))
    if utxos == []:
        print("Creator provided has no UTxOs in his address")
        exit(1)

    if parser_args[0].transaction_type == "oracle_request":
        sub_parser = argparse.ArgumentParser(parents=[parser])

        sub_parser.add_argument("-p", "--proposal_id", default="test_proposal_id")
        sub_parser.add_argument("-d", "--deadline", default=0)
        sub_parser.add_argument("-o", "--oracles", nargs="+", required=True)
        sub_parser.add_argument("-m", "--min_signatures", type=int, required=True)
        sub_parser.add_argument("-a", "--payment_address", required=True)
        sub_parser.add_argument(
            "-n", "--nft", required=False, default=None
        )  # policy.asset_name
        sub_parser.add_argument("-r", "--results", required=False, default=None)

        args = sub_parser.parse_args()

        dummy_minting_policy = pyc.ScriptHash.from_primitive(
            "02aa7e9d83f43ad54ab2585900292db7280ec43410e7563dac934d17"
        )

        datum = data_types.oracle_datum(
            args.proposal_id,
            dummy_minting_policy,
            vkey.hash(),
            int(args.deadline),
            [bytes.fromhex(oracle) for oracle in args.oracles],
            args.min_signatures,
            pyc.Address.from_primitive(args.payment_address),
            bytes(args.results, "utf-8") if args.results else None
        )

        with open("./scripts/oracle.plutus", "r") as f:
            script_hex = f.read()

            script_value = (
                pyc.Value.from_primitive(
                    [
                        10_000_000,
                        {
                            args.nft.split(".")[0]: {
                                bytes.fromhex(args.nft.split(".")[1]): 1
                            }
                        },
                    ]
                )
                if args.nft
                else 10_000_000
            )

            transaction = cardano.create_data_request(
                chain_context,
                utxos,
                address,
                script_hex,
                script_value,
                datum,
            )

            print("======== Transaction =========")
            print(transaction)
            print("==============================")

            signed_tx = cardano.assemble_transaction(transaction, skey)

            chain_context.submit_tx(signed_tx.to_cbor())

            print("==============================")
            print(f"Transaction {signed_tx.transaction_body.id} submitted successfully")
    elif parser_args[0].transaction_type == "oracle_respond":
        sub_parser = argparse.ArgumentParser(parents=[parser])
        sub_parser.add_argument("-i", "--input", required=True)
        sub_parser.add_argument("-r", "--results", required=True)
        sub_parser.add_argument("-s", "--signatures", nargs="+", required=True)

        args = sub_parser.parse_args()

        tx_hash, index = args.input.split("#")
        input_utxo = cardano.utxo_from_input(api, tx_hash, int(index))

        with open("./scripts/oracle.plutus", "r") as f:
            script_hex = f.read()

            datum = data_types.datum_from_cbor(input_utxo.output.datum.cbor)

            plutus_credential = datum.items[6]

            payment_address = pyc.Address(
                payment_part=pyc.VerificationKeyHash.from_primitive(
                    plutus_credential.payment_part
                ),
                network=pyc.Network.TESTNET,
            )

            transaction = cardano.submit_oracles_data(
                chain_context,
                utxos[0],
                input_utxo,
                script_hex,
                datum,
                payment_address,
                bytes(args.results, "utf-8"),
                [bytes.fromhex(sig) for sig in args.signatures],
            )

            signed_tx = cardano.assemble_transaction(transaction, skey)

            chain_context.submit_tx(signed_tx.to_cbor())

            print(f"Transaction {signed_tx.transaction_body.id} submitted successfully")
    elif parser_args[0].transaction_type == "escrow_create":
        sub_parser = argparse.ArgumentParser(parents=[parser])

        sub_parser.add_argument("-n", "--nft_policy", required=True)
        sub_parser.add_argument("-d", "--deadline", required=True)
        sub_parser.add_argument("-q", "--question_index", required=True)
        sub_parser.add_argument(
            "-v", "--vote_purpose", choices=["count", "weigth"], required=True
        )
        sub_parser.add_argument("-a", "--addresses", nargs="+", required=True)

        args = sub_parser.parse_args()

        datum = data_types.escrow_datum(
            pyc.ScriptHash.from_primitive(args.nft_policy),
            vkey.hash(),
            int(args.deadline),
            int(args.question_index),
            data_types.VoteUseCount()
            if args.vote_purpose == "count"
            else data_types.VoteUseWeight(),
            [pyc.Address.from_primitive(addr) for addr in args.addresses],
        )

        with open("./scripts/escrow.plutus", "r") as f:
            script_hex = f.read()

            transaction = cardano.create_escrow(
                chain_context,
                utxos,
                address,
                script_hex,
                10_000_000,
                datum,
            )

            print("======== Transaction =========")
            print(transaction)
            print("==============================")

            signed_tx = cardano.assemble_transaction(transaction, skey)

            chain_context.submit_tx(signed_tx.to_cbor())

            print("==============================")
            print(f"Transaction {signed_tx.transaction_body.id} submitted successfully")
    elif parser_args[0].transaction_type == "escrow_claim":
        sub_parser = argparse.ArgumentParser(parents=[parser])
        sub_parser.add_argument("-i", "--input", required=True)
        sub_parser.add_argument("-o", "--oracle_input", required=True)
        sub_parser.add_argument("-a", "--receiver_address", required=True)
        sub_parser.add_argument("-r", "--results", required=True)

        args = sub_parser.parse_args()

        tx_hash, index = args.input.split("#")
        input_utxo = cardano.utxo_from_input(api, tx_hash, int(index))

        tx_hash, index = args.oracle_input.split("#")
        oracle_input_utxo = cardano.utxo_from_input(api, tx_hash, int(index))

        with open("./scripts/escrow.plutus", "r") as f:
            script_hex = f.read()

            # Find collateral
            collateral = None
            for utxo in utxos:
                if isinstance(utxo.output.amount, int):
                    if utxo.output.amount >= 5_000_000:
                        collateral = utxo
                        break
                else:
                    if utxo.output.amount >= pyc.Value(5_000_000):
                        collateral = utxo
                        break

            if collateral is None:
                raise Exception("No collateral found")

            transaction = cardano.execute_escrow(
                chain_context,
                collateral,
                input_utxo,
                script_hex,
                oracle_input_utxo.input,
                pyc.Address.from_primitive(args.receiver_address),
                data_types.parse_vote_results(args.results)
            )

            signed_tx = cardano.assemble_transaction(transaction, skey)

            chain_context.submit_tx(signed_tx.to_cbor())

            print(f"Transaction {signed_tx.transaction_body.id} submitted successfully")
    


if __name__ == "__main__":
    main()
