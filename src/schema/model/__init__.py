# We need relative imports here to allow the `schema` package to be used without installation
# We need this for doing migrations from the production server
from .model import *
