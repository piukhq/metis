from setuptools import setup

from app.version import __version__

setup(
    name='metis',
    version=__version__,
    description=(
        'Card enrolment bridge API. '
        'Handles enrolment and unenrolment of payment cards with Visa, Amex, and Mastercard.'),
    url='https://git.bink.com/Olympus/metis',
    author='Chris Latham',
    author_email='cl@bink.com',
    zip_safe=True)
