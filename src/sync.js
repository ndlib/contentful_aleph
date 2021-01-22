const fetch = require('node-fetch')
const sleep = require('util').promisify(setTimeout)
const { t: typy } = require('typy')
const { getAleph, isDifferent, updateContentful, publishContentful } = require('./shared/helpers')
const { successResponse } = require('./shared/response')
const { sentryWrapper } = require('./shared/sentryWrapper')

// Issue: the first response that returns the api limit header will have actually gone through
// successfully - all the subsequent calls will fail until the limit is lifted. This is great
// except that we're in threads so we don't know if we're the first one to hit the error or not
// so we retry everything. If we retry a previously successful call we'll now get a version mismatch error

// The contentful calls per second is 10, so do 5 at a time (update + publish = 10 max calls) to get around ^ issue
const concurrentItems = 5

const updateItem = async (item) => {
  const alephNumber = typy(item, 'fields.alephSystemNumber.en-US').safeString
  const sysId = typy(item, 'sys.id').safeString

  if (!alephNumber) {
    console.warn(`No Aleph number for ${sysId}`)
    return
  }

  const alephItem = await getAleph(alephNumber)
  if (!alephItem) {
    console.warn(`Couldn't find item ${alephNumber}`)
    return
  }

  if (isDifferent(alephItem, item.fields)) {
    const version = typy(item, 'sys.version').safeNumber

    const updated = await updateContentful(sysId, version, alephItem, item.fields)
    if (!updated) {
      // Return the sysId so we know which records were processed, even though there are no changes
      return sysId
    }
    return publishContentful(sysId, typy(updated, 'sys.version').safeNumber)
  }
}

// Process items
const queueUpdates = async (items, start) => {
  const promises = []
  const use = items.slice(start, start + concurrentItems)

  console.log(`Processing items ${start} through ${start + use.length - 1}.`)

  use.forEach(item => {
    promises.push(updateItem(item))
  })

  return Promise.allSettled(promises).then(results => {
    const successful = []
    const errored = []

    results.forEach(result => {
      if (result.status === 'fulfilled') {
        if (result.value) {
          successful.push(result.value)
        }
      } else {
        const errorObj = result.reason.status
          ? {
            url: result.reason.url,
            status: result.reason.status,
            statusText: result.reason.statusText,
          }
          : result.reason
        errored.push(errorObj)
      }
    })
    return {
      successful: successful,
      errors: errored,
    }
  })
}

module.exports.handler = sentryWrapper(async (event, context, callback) => {
  // Build request
  const headers = {
    Authorization: `Bearer ${process.env.CONTENTFUL_MANAGEMENT_TOKEN}`,
  }
  const url = `${process.env.CONTENTFUL_CMA_URL}/entries?content_type=resource&order=sys.updatedAt&limit=1000`

  const response = await fetch(url, { headers: headers }).then(res => res.json())

  // Make list of items; exclude archived records
  const publishedItems = typy(response, 'items').safeArray.filter(item => {
    return typy(item, 'sys.archivedAt').isNullOrUndefined
  })

  console.log(`Updating ${publishedItems.length} items`)

  const promiseResults = {
    successful: [],
    errors: [],
  }

  let start = 0
  // wait before next call to make it less likely we hit the contentful api limit
  while (start < publishedItems.length) {
    const chunkResults = await queueUpdates(publishedItems, start)
    console.log('Chunk results:', JSON.stringify(chunkResults, null, 2))
    promiseResults.successful = promiseResults.successful.concat(chunkResults.successful)
    promiseResults.errors = promiseResults.errors.concat(chunkResults.errors)

    start += concurrentItems
    await sleep(1000) // Delay before next iteration to reduce risk of hitting API limits
  }

  return successResponse(callback, promiseResults, (promiseResults.errors.length > 0 ? 207 : 200))
})
