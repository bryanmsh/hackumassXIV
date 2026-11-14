import os
import tempfile

# Set before any api module is imported, so tests never write into the repo's data folder.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mirai-test-")
