import logging, os, requests, json, time, signal, sys
from datetime import datetime

def get_config():
    return {
        "ZONE_ID": str(os.environ.get("CF_UPDATER_ZONE_ID", "")),
        "A_RECORD": os.environ.get("CF_UPDATER_A_RECORD", None),
        "AAAA_RECORD": os.environ.get("CF_UPDATER_AAAA_RECORD", None),
        "TOKEN": str(os.environ.get("CF_UPDATER_TOKEN", "")),
        "LOGLEVEL": str(os.environ.get("CF_UPDATER_LOGLEVEL", "INFO")),
        "INTERVAL": int(os.environ.get("CF_UPDATER_INTERVAL", "30")),
        "FORCE_INTERVAL": str(os.environ.get("CF_UPDATER_FORCE_INTERVAL", "False")).lower() == "true"
    }

def signal_handler(sig, frame):
    logging.info("Recevied signal " + str((signal.Signals(sig).name)) + ". Shutting down.")
    sys.exit(0)

def check_settings(config):
    error = False
    if not config["ZONE_ID"]:
        logging.critical("CF_UPDATER_ZONE_ID is not set. This is required. Exiting.")
        error = True
    if config["A_RECORD"] is None and config["AAAA_RECORD"] is None:
        logging.critical("One of CF_UPDATER_A_RECORD or CF_UPDATER_AAAA_RECORD is required. Exiting.")
        error = True
    if config["A_RECORD"] is not None and config["AAAA_RECORD"] is not None:
        logging.critical("CF_UPDATER_A_RECORD and CF_UPDATER_AAAA_RECORD can't be used at the same time. Exiting.")
        error = True
    if not config["TOKEN"]:
        logging.critical("CF_UPDATER_TOKEN is not set. This is required. Exiting.")
        error = True
    if (int(config["INTERVAL"]) < 5 and config["FORCE_INTERVAL"] == False):
        logging.info("It's not recommended to set CF_UPDATER_INTERVAL to a value less than 5. Your value is %s. Default value is 30.", config["INTERVAL"])
        logging.info("Set CF_UPDATER_FORCE_INTERVAL = True to ignore this warning.")
        error = True
    return 1 if error else 0

def get_public_ip_v4():
    response = requests.get("https://ipinfo.io/ip")
    logging.info("Public IPv4 is: " + response.text)
    return response.text

def get_public_ip_v6():
    response = requests.get("https://v6.ipinfo.io/ip")
    logging.info("Public IPv6 is: " + response.text)
    return response.text

def get_zone_data(zone_id, token, record, type):
    if not zone_id or not token:
        logging.error("ZONE_ID or TOKEN is missing.")
        return [None, None]
    url = "https://api.cloudflare.com/client/v4/zones/" + str(zone_id) + "/dns_records"
    headers = {"Authorization": "Bearer " + str(token)}
    response = requests.get(url, headers=headers)
    response_json = response.json()
    for result in response_json["result"]:
        if (result["name"] == record and result["type"] == type):
            logging.debug("Found IP for " + type + "-Record " + record + ": " + result["content"] + ".")
            return [result["id"], result["content"]]
    logging.error("Can't find IP for " + type + "-Record " + record +". Are you sure it's set up at Cloudflare?")
    return [None, None]

def update_record(zone_id, token, record_id, record_ip, A_record, type):
    if not zone_id or not token or not record_id:
        logging.error("Missing required information for update_record.")
        return {}
    url = "https://api.cloudflare.com/client/v4/zones/" + str(zone_id) + "/dns_records/" + str(record_id)
    headers = {"Authorization": "Bearer " + str(token), "Content-Type": "application/json"}
    data = {
        "content": record_ip,
        "name": A_record,
        "type": type,
        "ttl": 60
    }
    logging.info("Updating record %s.", A_record)
    response = requests.put(url, headers=headers, data=json.dumps(data))
    logging.debug(response)
    response_text = json.loads(response.text)
    print(json.dumps(response_text))
    return response_text

def reconcile(config):
    logging.info("Starting reconciliation run.")
    try:
        f = open("./lastRun.epoch", "w")     # Relevant for health.sh / health-compose.sh
        f.write(str(round(datetime.now().timestamp())))
        f.close()
    except Exception as e:
        logging.error("Could not write lastRun.epoch: %s", e)
    
    if config["A_RECORD"]:
        dns_type = "A"
        public_ip = get_public_ip_v4()
        record_name = str(config["A_RECORD"])
    elif config["AAAA_RECORD"]:
        dns_type = "AAAA"
        public_ip = get_public_ip_v6()
        record_name = str(config["AAAA_RECORD"])
    else:
        logging.error("Neither A_RECORD nor AAAA_RECORD is set.")
        return

    record_id, record_ip = get_zone_data(str(config["ZONE_ID"]), str(config["TOKEN"]), record_name, dns_type)

    if record_id is None:
        return

    if (record_ip != public_ip):
        logging.info("Record IP for " + record_name + ": " + str(record_ip) +" does not match public IP of the host: " + public_ip + ".")
        update_record(str(config["ZONE_ID"]), str(config["TOKEN"]), str(record_id), public_ip, record_name, dns_type)
    else:
        logging.info("DNS record IP for " + record_name + ": " + str(record_ip) +" matches public IP of the host: " + public_ip + ".")
        logging.info("Nothing to do.")

def main():
    config = get_config()
    logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', encoding='utf-8')
    logging.getLogger().setLevel(str(config["LOGLEVEL"]))

    logging.debug("Running with this configuration:")
    logging.info("LOGLEVEL: \t%s", config["LOGLEVEL"])
    logging.debug("ZONE_ID: \t%s", config["ZONE_ID"])
    logging.debug("A_RECORD: \t%s", config["A_RECORD"])
    logging.debug("AAAA_RECORD: \t%s", config["AAAA_RECORD"])
    logging.debug("INTERVAL: \t%s", config["INTERVAL"])
    logging.debug("FORCE_INTERVAL: %s", config["FORCE_INTERVAL"])

    if (check_settings(config) != 0):
        logging.error("Failed settings check. Exit.")
        return 1

    while(True):
        reconcile(config)
        logging.info("Sleeping for %ss.", config["INTERVAL"])
        time.sleep(float(config["INTERVAL"]))

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()