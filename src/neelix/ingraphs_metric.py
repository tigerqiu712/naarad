import logging
import os
from neelix.metric import Metric
import neelix.metric
from linkedin import ingraphs
import datetime
import pytz
from pytz import timezone

logger = logging.getLogger('neelix.IngraphsMetric')

class IngraphsMetric(Metric):
  """ Class for Ingraphs rrds, deriving from class Metric """
  calc_metrics = None
  def __init__(self, metric_type, infile, access, outdir, label, ts_start, ts_end, **other_options):
    Metric.__init__(self, metric_type, infile, access, outdir, label, ts_start, ts_end)
    self.consolidate = None
    self.resolution = None
    for (key,val) in other_options.iteritems():
      setattr(self, key, val)
    #inGraphs data is always in PDT
    self.timezone = "PDT"

  def collect(self):
    """Fetch data from ingraphs and also parse to split out csvs """
    if self.access != 'ingraphs':
      logger.error("Incorrect access" + self.access + "set for Ingraphs metric. Cannot process this metric further")
      return False
    logger.info("Fetching and parsing ingraphs data: %s", self.infile)
    client = ingraphs.IngraphsClient()
    out_csv = self.get_csv()
    ingraphs_type = self.type
    #determine which type of data retrieval function to call
    if ingraphs_type == 'service':
      data_retrieval_func = client.service_data
    elif ingraphs_type == 'host':
      data_retrieval_func = client.host_data
    elif ingraphs_type == 'tag':
      data_retrieval_func = client.tag_data
    else:
      logger.error("ingraphs type can be either service, tag or host. Given: %s", ingraphs_type)
      return False
    #retrieve data and append into form high charts can understand
    rrd = self.infile
    ingraphs_response = data_retrieval_func(self.type_val, rrd, start=self.ts_start, end=self.ts_end, consolidate=self.consolidate, resolution=self.resolution)
    # Assuming only one timeseries returned
    if self.consolidate:
      data = ingraphs_response['data'][self.consolidate]
    else:
      data = ingraphs_response['data'][self.type_val]
    with open(out_csv, 'w') as FH:
      self.csv_files.append(out_csv)
      for ts in sorted(data):
        if data[ts] is None:
          logger.info("InGraphs: Skipping None data")
          continue
        #TODO(rmaheshw): Decide if you want to use reconcile_timezones method here or not
        dt = datetime.datetime.fromtimestamp(float(ts))
        #Initializing ts_string with local timezone conversion
        ts_string = dt.strftime("%Y-%m-%d %H:%M:%S")
        if self.graph_timezone == "UTC":
          utc = pytz.utc
          pst = timezone('US/Pacific')
          dt = pst.localize(dt)
          ts_string = dt.astimezone(utc).strftime("%Y-%m-%d %H:%M:%S")
        elif self.graph_timezone == "PST" or self.graph_timezone == "PDT":
          ts_string = dt.strftime("%Y-%m-%d %H:%M:%S")
        FH.write(ts_string)
        FH.write(',')
        FH.write(str(data[ts]))
        FH.write('\n')
    return True

  def get_csv(self):
    out_csv = os.path.join(self.outdir, "{0}.csv".format(self.metric_type))
    return out_csv

  def parse(self):
    return True
