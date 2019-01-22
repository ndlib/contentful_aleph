import os
dir_path = os.path.dirname(os.path.realpath(__file__))
import sys
sys.path.append(dir_path + "/lib/")

from hesburgh import heslog, hesutil
import json
import urllib2
import time

alephToCf = {
  "name": "title",
  "description": "description",
  "purl": "purl",
  "urls": "urls",
  "provider": "provider",
  "publisher": "publisher",
  "platform": "platform",
  "includes": "includes",
  "access": "access",
  "accessNotes": "accessNotes",
}

def isDifferent(alephItem, currentItem):
  if currentItem.get("databaseLetter", {}).get("en-US") is None:
    return True
  for aField, cfField in alephToCf.iteritems():
    if currentItem.get(cfField, {}).get("en-US") != alephItem.get(aField):
      return True
  return False


def getAleph(alephNumber):
  url = hesutil.getEnv("ALEPH_URL", throw=True)
  url = url.replace("<<systemNumber>>", alephNumber)

  req = urllib2.Request(url)
  return makeRequest(req, "aleph: %s" % alephNumber)


def makeRequest(req, meta):
  while True:
    try:
      response = urllib2.urlopen(req)
      return json.loads(response.read())
    except urllib2.HTTPError as e:
      # aleph likely timed out
      if e.code == 504:
        heslog.warn("Got a 504 - request timed out, retrying %s" % meta)
        continue

      resetHeader = e.headers.get("X-Contentful-RateLimit-Reset")
      if resetHeader and int(resetHeader) > 0:
        headerTime = int(resetHeader)
        heslog.warn("%s Hit contentful api limit, sleeping for %s" % (meta, headerTime))
        time.sleep(headerTime)
        continue

      heslog.error("Error code: %s  %s" % (e.code, meta))
      heslog.error(e.read())
      return False
    except urllib2.URLError as e:
      heslog.error(e.reason)
      return False


def updateContentful(entryId, version, alephItem, currentItem):
  heslog.info("Updating %s:%s" % (entryId, version))

  space = hesutil.getEnv("CONTENTFUL_SPACE", throw=True)
  url = hesutil.getEnv("CONTENTFUL_URL", throw=True)
  url = url.replace("<<spaceId>>", space).replace("<<entryId>>", entryId)

  # start with current fields, then overwrite what we want to
  #   This allows us to add fields to the content type without updating this script
  fields = currentItem

  for aField, cfField in alephToCf.iteritems():
    # Don't overwrite the title field
    if cfField == "title" and fields.get("title") is not None:
      continue

    fields[cfField] = { "en-US": alephItem.get(aField) }

  # add the databaseLetter field if it is blank
  if fields.get("databaseLetter") is None:
    fields["databaseLetter"] = { "en-US": alephItem.get("name")[0].lower() }
    if not alephItem.get("name")[0].isalpha():
      fields["databaseLetter"] = { "en-US": "#" }

  data = { "fields": fields }

  headers = {
    "Content-Type": "application/vnd.contentful.management.v1+json",
    "X-Contentful-Content-Type": "resource",
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
    "X-Contentful-Version": version,
  }

  req = urllib2.Request(url, data=json.dumps(data), headers=headers)
  req.get_method = lambda: 'PUT'
  return makeRequest(req, entryId)


def publishContentful(entryId, version):
  heslog.info("Publishing %s:%s" % (entryId, version))

  space = hesutil.getEnv("CONTENTFUL_SPACE", throw=True)
  url = hesutil.getEnv("CONTENTFUL_URL", throw=True)
  url = url.replace("<<spaceId>>", space).replace("<<entryId>>", entryId)
  url += "/published"

  headers = {
    "Content-Type": "application/vnd.contentful.management.v1+json",
    "X-Contentful-Content-Type": "resource",
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
    "X-Contentful-Version": version,
  }

  req = urllib2.Request(url, headers=headers)
  req.get_method = lambda: 'PUT'
  return makeRequest(req, entryId)
