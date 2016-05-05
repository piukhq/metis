import os
from app import create_app
from flask.ext.script import Manager

app = create_app()
manager = Manager(app)

HERE = os.path.abspath(os.path.dirname(__file__))
UNIT_TEST_PATH = os.path.join(HERE, 'app', 'tests', 'unit')

if __name__ == '__main__':
    manager.run()
