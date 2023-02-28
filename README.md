# Voteaire Escrow OffChain

The purpose of this repository is to have the necessary infrastructure for creating transactions which make use of our oracle script. This is a step further in the direction of allowing Voteaire users to make their voting information available for smart-contracts, allowing scripts, such as escrows, to have their behaviour determined by a specific vote.

## Cardano Lib

The `lib/cardano.py` is a module with some useful functions that are able to create transactions given some parameters.

The `create_data_request` function, for example, creates a transaction sending some arbitrary value to our oracle script with a specific datum. We call it a data request, because based on the datum and value inside that script, oracles can now be notified that they need to provide voting results for a specific ballot proposal and can act accordingly.

For instance, if the data request has a very small value, say 5 ADA. The oracles will be desincentivised and decide not to provide data for that script, because they would receive a very small payment in exchange.

If, however, they see a greater value inside the script (50 ADA) and see that the datum is correctly formatted (anyone could create any kind of corrupt script UTxO), the oracles can provide the voting results for Voteaires API, which mantain a collection of their signatures and execute a transaction once enough are provided.

Of course, the above example assumes oracles are human beings which are constaly looking at the blockchain for good offers. In reality, however, we intend to write software that will automatically look at the chain for new proposals, analyse it to determine if it is a good deal and, if so, send the results to Voteaires API.

## Integration Test

To make sure the `lib/cardano.py` functions are working properly, we created integration tests which create those transaction in a private testnet and assert that the outputs are correct. 

These tests can be found inside `integration-test/test/test_plutus.py` and can be executed by running `./run_tests.py` inside `integration-test` in a linux machine.

They were intially taken from `pycardano` repository which has the same folder, to which we owe a lot of credit, not only for its integration tests, but also for the library, which we use in most of our functions that interact with the cardano blockchain.

## Simulation

In order to actually see everything in action, we created the `src/simulate.py` file which is a CLI utility that allows you to create transactions in the actual blockchain. Because it uses pycardano with blockfrost, it requires you to provide a blockfrost project id. This can be done inside a `.env` file, which you must create inside `src`. Take a look at sample.env for more details.

To create a data request transaction, first you need a secret key and you need to fund it with some ADA so that we can create the transaction. Inside `keys`, you can run `./generate.py <name-of-wallet>` and it will create you a secret key and tell you its public key and address. Although it should be noticed that you will need to have cardano-cli installed in your system.
 
Alternatively, you can use pycardano to easily generate a secret key or whatever tool you prefer.

In our case, let's use `582037021be8046145f1d5b42d50ade182215d59b71d56d4619567424789a877d6f4`

Now, additionally, we will need a list of oracles, who will be the public keys responsible for providing us with the results. You can take a look at our `voteaire-escrow-contracts` repository, which inside contains a `utils/main.py` file where you can create those.

In this example, I have the following public keys
* `14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1`
* `f36f9a66f3916127e1ef303eef6cdde224c83da1fc46c3d948d2a68af62dced8`
* `c3e991c8919b4e2ff03cf2a795afe98c14b3d3ebe2e380598e8b8b46ddac28c4`

And I have their signatures for the string `"test"` which encoded in UTF-8 as a hexadecimal becomes `74657374`.
* `01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b`
* `102acc4091aa573b9cabf7bbcec53ca11e77d706a5681cbf25c57c11bb6029c31b6dd186c6d64438c99277dd8019a87d163a5b05b33bbe4f75627ce00943eb03`
* `a0bcc215d5c8d5689b3f9600ca95cf0b0fb7c7529b414f4c02b225ea283b205e106ad416c95be9eedbe24a71e6e5f80f4e64f4cf79eb1bb8a8ca180eb3661e00`

So let's create our first data request transaction.

First, get inside a poetry shell with `poetry shell`. If you don't have poetry installed, you can do it with `pip3 install poetry`.

If you haven't already, install the poetry dependencies with `poetry install` and now we are good to go.

```bash
python3 src/simulate.py -c 582037021be8046145f1d5b42d50ade182215d59b71d56d4619567424789a877d6f4 request -p test_proposal_id -d 0 -o 14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1 f36f9a66f3916127e1ef303eef6cdde224c83da1fc46c3d948d2a68af62dced8 c3e991c8919b4e2ff03cf2a795afe98c14b3d3ebe2e380598e8b8b46ddac28c4 -m 2 -a addr_test1vrsmdl7kdktx5japkh0qwxylq7zvhnk6j46vslnzcguz7cc7cyz6j
```

* `-p` identifies the proposal ID, in our case I'm using `"test_proposal_id"` but by Voteaire standards it would probably be some UUID like `34d11a6a-1a58-47b1-bba4-ab09d98a2bd9`.
* `-d` is the deadline after which the creator of this transaction can get his tokens back. This is specially useful if you send a great amount of ADA expecting the oracles to give you an answer, but they never do, which would mean that ADA would otherwise get lost forever
* `-o` is the list of oracles (their public keys)
* `-m` is the minimum number of signatures we require from those oracles for the results to be accepted (in this case we accept the majority, 2 out of 3)
* `-a` is the payment address to which the money from this script should be sent afterwards. This is so oracles have an incentive to particiapte.


You should receive something like this

```
...
==============================
Transaction fdbeb6c03b25764d7fe43c58d822b2996f0da275b1851232d0535fec46f4d052 submitted successfully
```

And after some time, you should be able to look at the [transaction](https://preprod.cardanoscan.io/transaction/fdbeb6c03b25764d7fe43c58d822b2996f0da275b1851232d0535fec46f4d052) in the blockchain.

You can run the `src/datum.py` file in this repository to inspect the datum from our output. It requires an `-i <txhash>#<txid>` as an argument.

So `python3 src/datum.py -i fdbeb6c03b25764d7fe43c58d822b2996f0da275b1851232d0535fec46f4d052#0` gives me:

```
{'proposal_id': 'test_proposal_id', 'minting_policy_identifier': ScriptHash(hex='02aa7e9d83f43ad54ab2585900292db7280ec43410e7563dac934d17'), 'creator': VerificationKeyHash(hex='6c29e3e756a5f7794792340b94b1426bab9ad61d87061a8c369f2009'), 'deadline': 0, 'oracles': [b'\x14\x88\x9c\xdbKr\xad\x10\xd4\xd4$<OP\x14\x1e\xea\x1d\x10\xa3H,\xd2\n}\xa6$]\x05\xea\x01\xf1', b"\xf3o\x9af\xf3\x91a'\xe1\xef0>\xefl\xdd\xe2$\xc8=\xa1\xfcF\xc3\xd9H\xd2\xa6\x8a\xf6-\xce\xd8", b'\xc3\xe9\x91\xc8\x91\x9bN/\xf0<\xf2\xa7\x95\xaf\xe9\x8c\x14\xb3\xd3\xeb\xe2\xe3\x80Y\x8e\x8b\x8bF\xdd\xac(\xc4'], 'min_signatures': 2, 'payment_address': addr_test1vrsmdl7kdktx5japkh0qwxylq7zvhnk6j46vslnzcguz7cc7cyz6j, 'results': None}
```

Which is exactly what we expected, now we have a script with 10 ADA inside and a datum requesting the oracles to give us the voting results for the Voteaire ballot proposal `test_proposal_id`.

Well, let's get those results and give them to our script.

As explained above, I have the signatures from our oracles for the string `test` (`74657374`), which are the following:

* `01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b`
* `102acc4091aa573b9cabf7bbcec53ca11e77d706a5681cbf25c57c11bb6029c31b6dd186c6d64438c99277dd8019a87d163a5b05b33bbe4f75627ce00943eb03`
* `a0bcc215d5c8d5689b3f9600ca95cf0b0fb7c7529b414f4c02b225ea283b205e106ad416c95be9eedbe24a71e6e5f80f4e64f4cf79eb1bb8a8ca180eb3661e00`

Let's use those to execute our next command, but since we only require 2 signatures, let's try only giving two and see if it works.

```
python3 src/simulate.py -c 582037021be8046145f1d5b42d50ade182215d59b71d56d4619567424789a877d6f4 respond -i fdbeb6c03b25764d7fe43c58d822b2996f0da275b1851232d0535fec46f4d052#0 -r 74657374 -s 01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b aa a0bcc215d5c8d5689b3f9600ca95cf0b0fb7c7529b414f4c02b225ea283b205e106ad416c95be9eedbe24a71e6e5f80f4e64f4cf79eb1bb8a8ca180eb3661e00
```

* We still need to provide our private key with the `-c` argument
* `-r` represents what results the oracles agreed about, in this case it's `"test"` hexadecimal representation after being encoded in utf-8 
* `-s` is the signatures from our oracles in the same order, notice our second signature is `aa`, which means our second oracle didn't provide any valid signature or disagreed about the results and so we are ignoring it

You should see something like this

```
Transaction 4919e98cceafc223d142e8d27c270e5495f2216b177edf36c160804467e505e0 submitted successfully
```

And after some time you should be able to see it in the [blockchain](https://preprod.cardanoscan.io/transaction/4919e98cceafc223d142e8d27c270e5495f2216b177edf36c160804467e505e0)

As you can see we sent 7.6 ADA to the payment address, the script enforces that it must be greater or equal to the input value (10 ADA) minus 3 ADA.

Most importantly, though, if we look at the datum, we can see that we now have our results `b"test"`.

`python3 src/datum.py -i 4919e98cceafc223d142e8d27c270e5495f2216b177edf36c160804467e505e0#0`

```
{'proposal_id': 'test_proposal_id', 'minting_policy_identifier': ScriptHash(hex='02aa7e9d83f43ad54ab2585900292db7280ec43410e7563dac934d17'), 'creator': VerificationKeyHash(hex='6c29e3e756a5f7794792340b94b1426bab9ad61d87061a8c369f2009'), 'deadline': 0, 'oracles': [b'\x14\x88\x9c\xdbKr\xad\x10\xd4\xd4$<OP\x14\x1e\xea\x1d\x10\xa3H,\xd2\n}\xa6$]\x05\xea\x01\xf1', b"\xf3o\x9af\xf3\x91a'\xe1\xef0>\xefl\xdd\xe2$\xc8=\xa1\xfcF\xc3\xd9H\xd2\xa6\x8a\xf6-\xce\xd8", b'\xc3\xe9\x91\xc8\x91\x9bN/\xf0<\xf2\xa7\x95\xaf\xe9\x8c\x14\xb3\xd3\xeb\xe2\xe3\x80Y\x8e\x8b\x8bF\xdd\xac(\xc4'], 'min_signatures': 2, 'payment_address': addr_test1vrsmdl7kdktx5japkh0qwxylq7zvhnk6j46vslnzcguz7cc7cyz6j, 'results': b'test'}
```

This means now any smart contract can use this information to determine some kind of behaviour. For instance, an escrow smart contract.


## Results Standard

The results string which should be singed by the oracles must follow this format:

"<question1choice1>,<question1choice2>,...|<question2choice1>,<question2choice2>,...|..."

Meaning the voting weight for each choice should be separated by `,` while the questions should be separated by `|`.

For example, for this [ballot](https://voteaire.io/results/b77d4209-71d1-4c85-9677-d6b98141ad11), we would have the following results:

`"578,214693|484,214787|578,214693"`