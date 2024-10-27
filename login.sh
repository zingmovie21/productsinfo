#!/bin/bash
echo ..........................................................
echo "Fetching Public URL..."
echo IP:
curl -s http://localhost:3389/api/tunnels | grep -o '"public_url":"[^"]*' | sed 's/"public_url":"//'
echo Username: curseofwitcher
echo Password: Howsthejosh@149
