const util = jest.requireActual('util')

const realPromisify = util.promisify

util.promisify = (...args) => {
  if (args[0] === setTimeout) {
    // Instantly return a resolved promise instead of waiting
    return () => Promise.resolve()
  }
  return realPromisify(...args)
}

module.exports = util
