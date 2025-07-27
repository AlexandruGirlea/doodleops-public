from datetime import datetime
import sys

"""
How to use:

python scripts/generate_timestamp.py 11-11-2021

or

python scripts/generate_timestamp.py
Enter date {dd-mm-yyyy}: 11-11-2021
"""

date_str = (
    sys.argv[1] if len(sys.argv) > 1 else input("\n\nEnter date {dd-mm-yyyy}:")
)
timestamp = datetime.strptime(date_str, "%d-%m-%Y").timestamp()
print("\n\n", "Timestamp:", timestamp, "\n")
