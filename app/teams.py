import requests

from settings import TEAMS_WEBHOOK_URL


def payment_card_notify(message):
    """
    Sends `message` to the 'Alerts - <environment>' channel on Microsoft Teams.
    """
    template = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "1A1F71",
        "summary": "Metis Event Notification",
        "Sections": [
            {
                "activityTitle": "Metis Event Notification",
                "facts": [
                    {"name": "Message", "value": message},
                ],
                "markdown": False,
            }
        ],
    }
    return requests.post(TEAMS_WEBHOOK_URL, json=template)
