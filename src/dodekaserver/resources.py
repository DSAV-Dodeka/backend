from pathlib import Path

# This depends on the 'resouces' folder being in the same folder as this file
# It fully resolves the path
res_path = Path(__file__).absolute().parent.joinpath("resources").resolve()
