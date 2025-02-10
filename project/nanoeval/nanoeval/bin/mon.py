import subprocess

import nanoeval.monitor as monitor

if __name__ == "__main__":
    subprocess.check_call(["streamlit", "run", monitor.__file__])
