const { t: typy } = require('typy')
const { getAleph, isDifferent, updateContentful } = require('./shared/helpers')
const { successResponse, errorResponse } = require('./shared/response')
const { sentryWrapper } = require('./shared/sentryWrapper')

module.exports.handler = sentryWrapper(async (event, context, callback) => {
  const headers = typy(event, 'headers').safeObject
  if (!headers) {
    return errorResponse(callback, 'Unrecognized event.', 422)
  }

  const cfTopic = headers['X-Contentful-Topic']
  if (!cfTopic) {
    console.error('Missing header X-Contentful-Topic')
    return errorResponse(callback, 'Unrecognized event.', 422)
  }

  const topicRegex = /^ContentManagement\.Entry\.(.+)/
  const topicMatch = topicRegex.exec(cfTopic)
  if (!topicMatch || !topicMatch[1]) {
    console.error('No topic match')
    return errorResponse(callback, 'Unrecognized event.', 422)
  }

  const eventType = topicMatch[1]
  if (eventType !== 'auto_save') {
    console.warn('Topic is not one we care about')
    return successResponse(callback, '', 304)
  }

  const body = JSON.parse(typy(event, 'body').safeString)
  const sysId = typy(body, 'sys.id').safeString
  if (!sysId) {
    console.error('No sysId')
    return errorResponse(callback, 'Invalid Contentful entry.', 422)
  }

  const alephNumber = typy(body, 'fields.alephSystemNumber.en-US').safeString
  if (!alephNumber) {
    console.error('No Aleph number')
    return successResponse(callback, 'No Aleph number found.', 304)
  }

  const alephItem = await getAleph(alephNumber)

  // If anything is different, update it
  // This should stop a potential infinite update loop
  if (isDifferent(alephItem, body.fields)) {
    await updateContentful(sysId, typy(body, 'sys.version').safeNumber, alephItem, body.fields)
  }

  return successResponse(callback)
})
