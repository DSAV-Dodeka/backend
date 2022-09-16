from pathlib import Path

# This depends on the 'resouces' folder being in the same folder as this file
# It fully resolves the path
res_path = Path(__file__).absolute().parent.joinpath("resources").resolve()

# Only use for development when this file is located in a project with src/apiserver
project_path = Path(__file__).absolute().parent.parent.parent.resolve()
