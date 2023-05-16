import hashlib
import hmac

from loguru import logger

from app.factory import create_factory
from app.teams import payment_card_notify


class Spreedly(object):
    provider = "spreedly"

    def __init__(self, provider):
        assert self.provider == provider

    # https://docs.spreedly.com/guides/payment-method-distribution/batch-export/#callback
    def save(self, data):
        for transaction in data["transactions"]:
            exclusions = transaction["payment_methods_excluded"]
            if exclusions:
                logger.warning(
                    "transaction {}: the following payment methods were excluded:\n{}".format(
                        transaction["token"], exclusions
                    )
                )
            else:
                logger.info("transaction {} was processed successfully.".format(transaction["token"]))
            logger.info("a transaction file was created at {}".format(transaction["url"]))

            # TODO(cl): get this transaction file exported to Visa.
        payment_card_notify("Received notify request from Spreedly.")


def signature_for(root, secret, xml):
    for signed in root.findall("transaction/signed"):
        hash = {
            "MD5": hashlib.md5,
            "SHA1": hashlib.sha1,
            "SHA256": hashlib.sha256,
            "SHA512": hashlib.sha512,
        }

        signature = signed.find("signature").text
        algorithm = signed.find("algorithm").text
        fields = signed.find("fields").text.split(" ")
        values = []
        for field in fields:
            val = root.find("transaction/" + field)
            if val.text is not None:
                values.append(val.text)
            else:
                values.append("")

        signature_data = "|".join(values)
        signature_data_bytes = signature_data.encode("utf-8")
        secret_key = secret.encode("utf-8")
        hash_function = hash.get(algorithm.upper())
        result = hmac.new(secret_key, msg=signature_data_bytes, digestmod=hash_function).hexdigest()
        return hmac.compare_digest(result, signature)


def register():
    factory = create_factory("process_agents")
    factory.register("spreedly", Spreedly)
