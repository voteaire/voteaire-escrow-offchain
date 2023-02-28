from fixtures import api

import pycardano as pyc


def test_oracle_submit(api, monkeypatch):
    from model import Signature

    client, _ = api

    class MockBlockfrostApi:
        def __init__(self, **args):
            pass

    utxo = pyc.UTxO(
        pyc.TransactionInput(
            pyc.TransactionId.from_primitive(
                "5e0cba9e817823ce82c32ded0b22f6790f075cd39ae9e0ab9af7ad1cc81edf17"
            ),
            0,
        ),
        pyc.TransactionOutput(
            pyc.Address.from_primitive(
                "addr_test1vpacm899akkpck3u0zmjndfsppapqrxstqq38nwvm0xv7wcjxzzqy"
            ),
            10_000_000,
            datum=pyc.RawCBOR(
                b"\x9fPtest_proposal_idX\x1c\x02\xaa~\x9d\x83\xf4:\xd5J\xb2XY\x00)-\xb7(\x0e\xc44\x10\xe7V=\xac\x93M\x17X\x1cl)\xe3\xe7V\xa5\xf7yG\x924\x0b\x94\xb1Bk\xab\x9a\xd6\x1d\x87\x06\x1a\x8c6\x9f \t\x00\x9fX \x14\x88\x9c\xdbKr\xad\x10\xd4\xd4$<OP\x14\x1e\xea\x1d\x10\xa3H,\xd2\n}\xa6$]\x05\xea\x01\xf1X \xf3o\x9af\xf3\x91a'\xe1\xef0>\xefl\xdd\xe2$\xc8=\xa1\xfcF\xc3\xd9H\xd2\xa6\x8a\xf6-\xce\xd8X \xc3\xe9\x91\xc8\x91\x9bN/\xf0<\xf2\xa7\x95\xaf\xe9\x8c\x14\xb3\xd3\xeb\xe2\xe3\x80Y\x8e\x8b\x8bF\xdd\xac(\xc4\xff\x02\xd8y\x9fX\x1c\xe1\xb6\xff\xd6m\x96jK\xa1\xb5\xde\x07\x18\x9f\x07\x84\xcb\xce\xda\x95t\xc8~b\xc28/c\xff\xd8y\x9fDtest\xff\xff"
            ),
        ),
    )

    print(utxo)

    monkeypatch.setattr("api.oracles.BlockFrostApi", MockBlockfrostApi)
    monkeypatch.setattr(
        "api.oracles.cardano.utxo_from_input",
        lambda *_: utxo,
    )
    monkeypatch.setattr(
        "api.oracles.signature.enforce_standard",
        lambda *_: True,
    )

    response = client.post(
        "/oracle/test_proposal_id/submit",
        json={
            "transaction_hash": "hash",
            "index": 0,
            "pubkey": "14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1",
            "signature": "01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b",
            "results": "test",
        },
    )

    assert response.status_code == 200
    assert response.json == {"success": True}

    signatures = Signature.query.all()

    assert len(signatures) == 1
    signature: Signature = signatures[0]

    assert signature.proposal_id == "test_proposal_id"
    assert (
        signature.pubkey
        == "14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1"
    )
    assert (
        signature.signature
        == "01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b"
    )
    assert signature.results == "test"

    assert signature.script_input == "hash#0"

    response = client.post(
        "/oracle/test_proposal_id/submit",
        json={
            "transaction_hash": "hash",
            "index": 0,
            "pubkey": "14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1",
            "signature": "01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b",
            "results": "test-fake",
        },
    )

    assert response.status_code == 200
    assert response.json == {"success": False, "message": "Invalid signature"}

    response = client.post(
        "/oracle/test_proposal_id/submit",
        json={
            "transaction_hash": "hash",
            "index": 0,
            "pubkey": "14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1",
            "signature": "102acc4091aa573b9cabf7bbcec53ca11e77d706a5681cbf25c57c11bb6029c31b6dd186c6d64438c99277dd8019a87d163a5b05b33bbe4f75627ce00943eb03",
            "results": "test",
        },
    )

    assert response.status_code == 200
    assert response.json == {"success": False, "message": "Invalid signature"}

    response = client.post(
        "/oracle/test_proposal_id/submit",
        json={
            "transaction_hash": "hash",
            "index": 0,
            "pubkey": "74ca8a3406d265acc80e03ee9caf4bef5ccd3686cc29cf24f4a3a1418765f3ac",
            "signature": "b5575bb1e61b9734f1f954a0b2ee048c73d2210df1f37f6cc2bbce5e8e20a396f6d103745d4c3ca454bc50974431f8136e246616380588f7d4a7671ad63f800e",
            "results": "test",
        },
    )

    assert response.status_code == 200
    assert response.json == {"success": False, "message": "PubKey not within valid oracles"}