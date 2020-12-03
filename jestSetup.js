// Include the .env file to load environment variable values for jest tests
const fs = require('fs')
const dotenv = require('dotenv')
const envConfig = dotenv.parse(fs.readFileSync('test/.env'))
for (const k in envConfig) {
  process.env[k] = envConfig[k]
}
