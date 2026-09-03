"""config.py — the single place that defines paths, constants and label maps.

Why one config file?
  Every script in this project needs the same facts:
    * where the raw / processed data lives,
    * what each dataset is called,
    * how the raw attack labels map to the coarse categories we predict.
  If those facts were hard-coded in ten different files, changing a path or
  a mapping would mean hunting through every script. Keeping them here means
  there is ONE place to look and ONE place to edit.

  This file is "just data" — it does no work, it only defines values.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# ROOT_DIR is the project root = D:\Cyber threat Detection
# (config.py lives in src/utils/, so going up two folders lands on the root)
ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_RAW_DIR = ROOT_DIR / "data" / "raw"            # original dataset files
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"  # cleaned data (Phase 2)
REPORTS_DIR = ROOT_DIR / "reports"                  # generated reports
MODELS_DIR = ROOT_DIR / "src" / "models" / "registry"  # saved models (Phase 3)
FRONTEND_PUBLIC_DIR = ROOT_DIR / "frontend" / "public"  # charts served to UI

# ---------------------------------------------------------------------------
# Common label schema
# ---------------------------------------------------------------------------
# Both datasets are converted to this SAME set of columns, so every
# downstream step (EDA, preprocessing, training, the API) only ever sees
# one format.  A "row" is one network connection/flow.
SOURCE_COL = "source"          # which dataset the row came from
IS_ATTACK_COL = "is_attack"    # 1 = attack, 0 = normal traffic
CATEGORY_COL = "attack_category"  # coarse class: Normal / DoS / Probe / R2L / U2R ...
TYPE_COL = "attack_type"       # fine-grained attack name (e.g. neptune, DDoS)

NORMAL_CATEGORY = "Normal"     # the value used when traffic is benign

# ---------------------------------------------------------------------------
# NSL-KDD
# ---------------------------------------------------------------------------
NSL_KDD_RAW_DIR = DATA_RAW_DIR / "nsl-kdd"
NSL_KDD_TRAIN_FILE = NSL_KDD_RAW_DIR / "KDDTrain+.txt"   # 125,973 rows
NSL_KDD_TEST_FILE = NSL_KDD_RAW_DIR / "KDDTest+.txt"     #  22,544 rows

# The 41 feature names of NSL-KDD, in file order.
# (These are the columns the dataset's documentation defines. The .txt files
#  actually have 43 fields: these 41 features + the label + a difficulty score.
#  The difficulty column is dropped at load time — see loader.py.)
NSL_KDD_FEATURES = [
    "duration", "protocol_type", "service", "flag",
    "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
    "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count",
    "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
    "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
]

# The only categorical (text) columns in NSL-KDD; everything else is numeric.
NSL_KDD_CATEGORICAL_FEATURES = ["protocol_type", "service", "flag"]

# Map each specific NSL-KDD attack name to its coarse class.
# This is the standard KDD Cup 99 / NSL-KDD grouping used throughout the
# literature. "worm" appears in the test set only 2 times, so its assignment
# (here: R2L) has negligible influence on results.
NSL_KDD_ATTACK_CATEGORY = {
    # --- DoS (Denial of Service): flood a service so it can't answer ---
    "back": "DoS", "land": "DoS", "neptune": "DoS", "pod": "DoS",
    "smurf": "DoS", "teardrop": "DoS", "apache2": "DoS", "udpstorm": "DoS",
    "processtable": "DoS", "mailbomb": "DoS",
    # --- Probe: scan the network to discover what is out there ---
    "ipsweep": "Probe", "nmap": "Probe", "portsweep": "Probe",
    "satan": "Probe", "saint": "Probe", "mscan": "Probe",
    # --- R2L (Remote-to-Local): unauthorised access from a remote machine ---
    "guess_passwd": "R2L", "ftp_write": "R2L", "imap": "R2L", "phf": "R2L",
    "multihop": "R2L", "warezmaster": "R2L", "warezclient": "R2L",
    "spy": "R2L", "xlock": "R2L", "xsnoop": "R2L", "snmpguess": "R2L",
    "snmpgetattack": "R2L", "httptunnel": "R2L", "named": "R2L",
    "sendmail": "R2L", "worm": "R2L",
    # --- U2R (User-to-Root): gain root/administrator privileges ---
    "buffer_overflow": "U2R", "loadmodule": "U2R", "perl": "U2R",
    "ps": "U2R", "rootkit": "U2R", "sqlattack": "U2R", "xterm": "U2R",
}

# ---------------------------------------------------------------------------
# CICIDS2017  (ML-ready version: 78 features + Label, one CSV per day)
# ---------------------------------------------------------------------------
CICIDS_RAW_DIR = DATA_RAW_DIR / "MachineLearningCSV" / "MachineLearningCVE"
# Matches all 8 daily files, e.g. Monday-WorkingHours.pcap_ISCX.csv
CICIDS_FILE_PATTERN = "*-WorkingHours*.csv"

# Map each CICIDS2017 label to its coarse category.
# NOTE: the raw labels are normalised before this map is used:
#   - leading/trailing spaces are stripped,
#   - the corrupted "\ufffd" (a replacement character left by an old
#     Windows-1252 em-dash) is turned into "-",
# so keys here use a plain dash.
CICIDS_ATTACK_CATEGORY = {
    "BENIGN": "Normal",
    "DDoS": "DDoS",
    "PortScan": "PortScan",
    "FTP-Patator": "Brute Force",
    "SSH-Patator": "Brute Force",
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "DoS slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "Heartbleed": "Heartbleed",
    "Bot": "Botnet",
    "Infiltration": "Infiltration",
    # "Web Attack - X" labels are handled by a startswith rule in the loader
    # (their exact spelling is unreliable in the provided files).
}

# ---------------------------------------------------------------------------
# CICIDS2017 column-name cleaning
# ---------------------------------------------------------------------------
# Raw headers look like " Total Fwd Packets", "Flow Bytes/s",
# "Fwd Header Length.1".  We normalise them to snake_case so the codebase
# uses consistent names (e.g. total_fwd_packets, flow_bytes_s).
# Columns that should NOT become model features (identifying metadata).
# NOTE: "destination_port" is deliberately NOT here — the ML-ready version
# counts it as one of its 78 features, and port number is a legitimate,
# non-identifying signal (port 80 ~= web, port 53 ~= DNS, port 22 ~= SSH).
CICIDS_META_COLUMNS = {
    "flow_id", "source_ip", "source_port", "destination_ip",
    "protocol", "timestamp",
}

# ---------------------------------------------------------------------------
# Random seeds — keep experiments reproducible for the thesis
# ---------------------------------------------------------------------------
RANDOM_STATE = 42
