import schedule
import time
from main import run

# Run immediately once
run()

# Then run every hour
schedule.every(1).hours.do(run)

while True:
    schedule.run_pending()
    time.sleep(60)