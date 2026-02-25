#!/bin/bash

#curl -X POST http://localhost:9999/agent/chat \
#  -H "Content-Type: application/json" \
#  -d '{"prompt":"Hello from curl"}'


curl -X POST http://localhost:9999/agent/zoey/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"send email to my friend about our trip to the beach, his email is marlito@gmail.com"}'