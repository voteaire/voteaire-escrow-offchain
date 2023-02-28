from flask import request
from blockfrost import BlockFrostApi
from nacl.exceptions import BadSignatureError

from lib import cardano, signature, environment
from model import Signature, db

import os


def submit(proposal_id: str):
    data = request.json

    if not signature.enforce_standard(data["results"]):
        return {"success": False, "message": "Results don't follow the standard"}

    try:
        signature.verify(
            data["pubkey"], bytes(data["results"], "utf-8").hex(), data["signature"]
        )
    except BadSignatureError:
        return {"success": False, "message": "Invalid signature"}

    env = environment.get_environment(["BLOCKFROST_PROJECT_ID", "NETWORK_MODE"])

    print(env["BLOCKFROST_PROJECT_ID"])

    api = BlockFrostApi(
        project_id=env["BLOCKFROST_PROJECT_ID"],
        base_url="https://cardano-preprod.blockfrost.io/api"
        if env["NETWORK_MODE"] == "testnet"
        else "https://cardano-mainnet.blockfrost.io/api",
    )

    # Verify whether this is one of the oracles in the UTxO
    script_input = cardano.utxo_from_input(api, data["transaction_hash"], data["index"])
    datum = cardano.cbor_datum_to_dict(script_input.output.datum.cbor)

    if not bytes.fromhex(data["pubkey"]) in datum["oracles"]:
        return {"success": False, "message": "PubKey not within valid oracles"}

    sig = Signature(
        proposal_id=proposal_id,
        pubkey=data["pubkey"],
        signature=data["signature"],
        results=data["results"],
        script_input=f"{data['transaction_hash']}#{data['index']}",
    )

    db.session.add(sig)
    db.session.commit()

    return {"success": True}, 200
