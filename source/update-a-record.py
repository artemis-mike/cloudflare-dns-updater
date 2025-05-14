import logging, os, requests, json, time, signal, sys
from datetime import datetime

ZONE_ID   = os.environ.get("CF_UPDATER_ZONE_ID", None)
A_RECORD  = os.environ.get("CF_UPDATER_A_RECORD", None)
TOKEN     = os.environ.get("CF_UPDATER_TOKEN", None)
LOGLEVEL  = os.environ.get("CF_UPDATER_LOGLEVEL", "INFO")

# CF API rate limit is 1200 requests / 5 miutes / user (https://developers.cloudflare.com/fundamentals/api/reference/limits/)
# We use a maximum of 2 requests per cycle (regularly 1 request per cycle if no changed are to be done).
# To stay save, the default interval is 30s (-> regularly 10 requests / 5 minutes)
INTERVAL        = int(os.environ.get("CF_UPDATER_INTERVAL", 30))
FORCE_INTERVAL  = os.environ.get("CF_UPDATER_FORCE_INTERVAL", False)

logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logging.getLogger().setLevel(LOGLEVEL)

def signal_handler(sig, frame):
  logging.info("Recevied signal " + str((signal.Signals(sig).name)) + ". Shutting down.")
  sys.exit(0)


def check_settings():
  error = False
  if (ZONE_ID is None):
    logging.critical("CF_UPDATER_ZONE_ID is not set. This is required. Exiting.")
    error = True
  if (A_RECORD is None):
    logging.critical("CF_UPDATER_A_RECORD is not set. This is required. Exiting.")
    error = True
  if (TOKEN is None):
    logging.critical("CF_UPDATER_TOKEN is not set. This is required. Exiting.")
    error = True
  if (INTERVAL < 5 and FORCE_INTERVAL == False):
    logging.info("It's not recommended to set CF_UPDATER_INTERVAL to a value less than 5. Your value is %s. Default value is 30.", INTERVAL)
    logging.info("Set CF_UPDATER_FORCE_INTERVAL = True to ignore this warning.")
    error = True
  if error is True:
    return 1
  else:
    return 0

def get_public_ip():
  response = requests.get("https://ipinfo.io/ip")
  logging.info("Public IP is: " + response.text)
  return response.text


def get_zone_data(zone_id, token, A_record):
  url = "https://api.cloudflare.com/client/v4/zones/" + zone_id + "/dns_records"
  headers = {"Authorization": "Bearer " + token}
  response = requests.get(url, headers=headers)
  response_json = response.json()
  for result in response_json["result"]:
    if (result["name"] == A_record):
      logging.debug("Found IP for A-Record " + A_record + ": " + result["content"] + ".")
      return [result["id"], result["content"]]
  logging.error("Can't find IP for A-Record " + A_record +". Are you sure it's set up at Cloudflare?")
  sys.exit(2) 

      

def update_record(zone_id, token, record_id, record_ip, A_record):
  url = "https://api.cloudflare.com/client/v4/zones/" + zone_id + "/dns_records/" + record_id
  headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
  data = {
    "content": record_ip,
    "name": A_record,
    "type": "A",
    "ttl": 60
  }
  logging.info("Updating record %s.", A_record)
  response = requests.put(url, headers=headers, data=json.dumps(data))
  logging.debug(response)
  response_text = json.loads(response.text)
  print(json.dumps(response_text))



def main():
  logging.debug("Running with this configuration:")
  logging.info("LOGLEVEL: \t%s", LOGLEVEL)
  logging.debug("ZONE_ID: \t%s", ZONE_ID)
  logging.debug("A_RECORD: \t%s", A_RECORD)
  logging.debug("INTERVAL: \t%s", INTERVAL)
  logging.debug("FORCE_INTERVAL: %s", FORCE_INTERVAL)

  if (check_settings() != 0):
    logging.error("Failed settings check. Exit.")
    return 1

  while(True):
    logging.info("Starting reconciliation run.")
    f = open("./lastRun.epoch", "w")     # Relevant for health.sh / health-compose.sh
    f.write(str(round(datetime.now().timestamp())))
    f.close()
    public_ip = get_public_ip()
    record_id, record_ip = get_zone_data(ZONE_ID, TOKEN, A_RECORD)
    if (record_ip != public_ip):
      logging.info("Record IP for " + A_RECORD + ": " + record_ip +" does not match public IP of the host: " + public_ip + ".")
      update_record(ZONE_ID, TOKEN, record_id, public_ip, A_RECORD)
    else:
      logging.info("DNS record IP for " + A_RECORD + ": " + record_ip +" matches public IP of the host: " + public_ip + ".")
      logging.info("Nothing to do. Sleeping for %ss.", INTERVAL)
      time.sleep(INTERVAL)


    


if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGHUP, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)

  main()